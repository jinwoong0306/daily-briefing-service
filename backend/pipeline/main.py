"""
뉴스 파이프라인 오케스트레이터

실행 모드:
  1) full      : 수집 -> 클러스터링 (기존 일괄)
  2) collect   : 수집만 수행 후 briefing_date staging에 누적
  3) finalize  : staging 누적 데이터로 클러스터링 + DB 적재
  4) brief     : Supabase articles -> Redis 사용자별 브리핑 캐시
  5) deliver   : Redis 브리핑 -> 앱 푸시 발송 경계

예시:
  python main.py collect
  python main.py finalize
  python main.py finalize --date 2026-04-05
  python main.py brief
  python main.py deliver
  python main.py full
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import pytz
from dateutil import parser as date_parser

from unified_crawler import (
    run_pipeline as run_unified_pipeline,
    acquire_process_lock,
)
from clustering import run_pipeline as run_clustering_pipeline
from ai_briefing import generate_and_cache_briefings
from push_delivery import deliver_cached_briefings
from supabase_uploader import (
    upload_articles_to_supabase,
    start_pipeline_run,
    finish_pipeline_run,
    fetch_user_keywords_from_supabase,
)
from staging_manager import (
    resolve_briefing_date_for_collection,
    resolve_briefing_date_for_finalize,
    append_articles_to_staging,
    load_staging,
    mark_staging_finalized,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_env_if_exists() -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("'").strip('"')


def load_config(config_path: str = CONFIG_PATH, validate_naver: bool = True) -> dict:
    load_env_if_exists()

    if not os.path.exists(config_path):
        logging.warning(f"설정 파일을 찾을 수 없습니다. Supabase/.env 설정으로 진행합니다: {config_path}")
        config = {}
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    api_config = config.get("api", {})
    naver_client_id = os.environ.get("NAVER_CLIENT_ID") or api_config.get("client_id")
    naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET") or api_config.get("client_secret")
    if validate_naver:
        if not naver_client_id or naver_client_id == "YOUR_CLIENT_ID":
            logging.error("❌ NAVER_CLIENT_ID 또는 config.json의 네이버 API Client ID를 입력해 주세요.")
            sys.exit(1)
        if not naver_client_secret or naver_client_secret == "YOUR_CLIENT_SECRET":
            logging.error("❌ NAVER_CLIENT_SECRET 또는 config.json의 네이버 API Client Secret을 입력해 주세요.")
            sys.exit(1)

    return config


def _parse_window_dt(value: str) -> datetime:
    dt = date_parser.parse(value)
    if dt.tzinfo is None:
        kst = pytz.timezone("Asia/Seoul")
        dt = kst.localize(dt)
    return dt


def resolve_keywords(config: dict) -> tuple[list[str], str]:
    """
    Supabase user_keywords를 우선 사용하고, 비어 있으면 config.json으로 fallback 합니다.
    """
    keyword_table = os.environ.get("SUPABASE_USER_KEYWORDS_TABLE", "user_keywords").strip() or "user_keywords"
    keywords = fetch_user_keywords_from_supabase(table_name=keyword_table)
    if keywords:
        logging.info(f"[KEYWORDS] Supabase {keyword_table}에서 {len(keywords)}개 키워드 로드")
        return keywords, "supabase"

    fallback_keywords = []
    seen = set()
    for keyword in config.get("keywords", []):
        normalized = str(keyword).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        fallback_keywords.append(normalized)

    if fallback_keywords:
        logging.warning(
            "[KEYWORDS] Supabase 키워드가 없어 config.json keywords로 fallback 합니다."
        )
        return fallback_keywords, "config"

    return [], "none"


def run_collect_mode(config: dict) -> None:
    keywords, keyword_source = resolve_keywords(config)
    if not keywords:
        logging.error("❌ 검색할 키워드가 없습니다. Supabase user_keywords 또는 config.json keywords를 확인해 주세요.")
        sys.exit(1)

    collect_pipeline_name = os.environ.get("COLLECTOR_PIPELINE_NAME", "collector_unified").strip() or "collector_unified"

    logging.info(f"[COLLECT] 수집 시작 (source={keyword_source}, 키워드: {', '.join(keywords)})")
    collected = run_unified_pipeline(
        keywords,
        pipeline_name=collect_pipeline_name,
        out_path=None,          # 누적 저장은 staging에서 관리
        upload_to_db=False,     # 야간 수집 단계에서는 DB 적재 생략
        record_run=True,
    )

    articles = collected.get("articles", [])
    meta = collected.get("meta", {})
    window_start = _parse_window_dt(meta["window_start_kst"])
    window_end = _parse_window_dt(meta["window_end_kst"])

    start_hour = int(os.environ.get("PIPELINE_COLLECTION_START_HOUR", "20"))
    end_hour = int(os.environ.get("PIPELINE_COLLECTION_END_HOUR", "6"))
    briefing_date = resolve_briefing_date_for_collection(
        ref_dt=window_end,
        start_hour=start_hour,
        end_hour=end_hour,
    )

    staging_result = append_articles_to_staging(
        briefing_date=briefing_date,
        new_articles=articles,
        window_start=window_start,
        window_end=window_end,
    )

    logging.info(
        "[COLLECT] 누적 저장 완료: "
        f"briefing_date={briefing_date}, incoming={staging_result['incoming_count']}, "
        f"added={staging_result['added_count']}, updated={staging_result['updated_count']}, "
        f"total={staging_result['total_after_merge']}, path={staging_result['path']}"
    )


def _resolve_finalize_window(staging_data: dict) -> tuple[datetime, datetime]:
    kst = pytz.timezone("Asia/Seoul")
    now_kst = datetime.now(kst)
    starts = []
    ends = []

    for run in staging_data.get("runs", []):
        ws = run.get("window_start_kst")
        we = run.get("window_end_kst")
        if ws:
            starts.append(_parse_window_dt(ws))
        if we:
            ends.append(_parse_window_dt(we))

    if starts and ends:
        return min(starts), max(ends)
    return now_kst, now_kst


def run_finalize_mode(config: dict, briefing_date: str = "") -> None:
    target_date = briefing_date or resolve_briefing_date_for_finalize()
    staging_data = load_staging(target_date)
    articles = staging_data.get("articles", [])

    if not articles:
        logging.warning(f"[FINALIZE] staging 데이터가 없습니다. briefing_date={target_date}")
        return

    kst = pytz.timezone("Asia/Seoul")
    finalizer_pipeline_name = os.environ.get("FINALIZER_PIPELINE_NAME", "finalize_briefing").strip() or "finalize_briefing"
    window_start, window_end = _resolve_finalize_window(staging_data)

    run_id = start_pipeline_run(
        pipeline_name=finalizer_pipeline_name,
        window_start=window_start.astimezone(pytz.UTC),
        window_end=window_end.astimezone(pytz.UTC),
    )

    try:
        # 1) 누적 기사 전체를 클러스터링 입력 파일로 구성
        os.makedirs("cache", exist_ok=True)
        merged_out = "cache/crawled_merged_news.json"
        merged_payload = {
            "meta": {
                "source": "staging_finalize",
                "briefing_date": target_date,
                "description": "야간 누적 수집(staging) 데이터 기반 최종 병합본",
                "window_start_kst": window_start.astimezone(kst).isoformat(),
                "window_end_kst": window_end.astimezone(kst).isoformat(),
                "run_count": len(staging_data.get("runs", [])),
            },
            "articles": articles,
        }
        with open(merged_out, "w", encoding="utf-8") as f:
            json.dump(merged_payload, f, ensure_ascii=False, indent=2)
        logging.info(f"[FINALIZE] 병합 입력 파일 생성: {merged_out} ({len(articles)}건)")

        # 2) 클러스터링 + clustered_result 업로드
        run_clustering_pipeline()

        # 3) 원문 기사 DB 적재 (클러스터링 이후)
        upload_result = upload_articles_to_supabase(articles)
        if upload_result.get("enabled"):
            logging.info(
                "[FINALIZE] articles DB 업로드 완료: "
                f"{upload_result.get('uploaded', 0)}건 "
                f"(prepared={upload_result.get('prepared', 0)}건)"
            )
        else:
            logging.info("[FINALIZE] Supabase 환경변수 미설정으로 articles 업로드를 건너뜁니다.")

        # 4) staging finalize 마킹 + archive 사본
        finalize_info = mark_staging_finalized(target_date, archive_copy=True)
        logging.info(
            "[FINALIZE] staging finalize 완료: "
            f"path={finalize_info.get('path')}, archive={finalize_info.get('archived_path')}"
        )

        finish_pipeline_run(run_id=run_id, status="success")
        logging.info(f"[FINALIZE] 완료: briefing_date={target_date}")

    except Exception as e:
        finish_pipeline_run(run_id=run_id, status="failed", error_message=str(e))
        logging.exception(f"[FINALIZE] 실패: {e}")
        raise


def run_full_mode(config: dict) -> None:
    keywords, keyword_source = resolve_keywords(config)
    if not keywords:
        logging.error("❌ 검색할 키워드가 없습니다. Supabase user_keywords 또는 config.json keywords를 확인해 주세요.")
        sys.exit(1)

    print("=" * 60)
    print("  🚀 핵심 뉴스 통합 파이프라인 (수집 -> 클러스터링 -> 시각화) 시작")
    print("=" * 60)

    print(f"\n[STEP 1] 뉴스 통합 스크래핑 파이프라인 가동 (source={keyword_source}, 키워드: {', '.join(keywords)})")
    run_unified_pipeline(keywords)

    print("\n[STEP 2] 뉴스 군집화 및 AI 기반 이슈 시각화 파이프라인 가동")
    run_clustering_pipeline()

    print("\n" + "=" * 60)
    print("  🎉 모든 파이프라인이 성공적으로 완료되었습니다!")
    print("  - 병합된 수집 원본: cache/crawled_merged_news.json")
    print("  - 주제별 그룹화 리포트: cache/clustered_result.json")
    print("  - 시각화 이미지 3종: cache/cluster_bar.png, similarity_hist.png, cluster_scatter.png")
    print("=" * 60)


def run_brief_mode(briefing_date: str = "") -> None:
    result = generate_and_cache_briefings(briefing_date=briefing_date or None)
    logging.info(
        "[BRIEF] Redis 브리핑 생성 완료: "
        f"date={result.get('briefing_date')}, subscriptions={result.get('subscriptions')}, "
        f"keywords={result.get('keywords')}, users={result.get('users')}, "
        f"redis_saved={result.get('redis_saved')}"
    )


def run_deliver_mode(briefing_date: str = "") -> None:
    result = deliver_cached_briefings(briefing_date=briefing_date or None)
    logging.info(
        "[DELIVER] 앱 푸시 발송 경계 실행 완료: "
        f"date={result.get('briefing_date')}, users={result.get('users')}, "
        f"tokens={result.get('push_tokens')}, attempted={result.get('attempted')}, "
        f"sent={result.get('sent')}, provider={result.get('provider')}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="뉴스 파이프라인 오케스트레이터")
    parser.add_argument(
        "mode",
        nargs="?",
        default="full",
        choices=["full", "collect", "finalize", "brief", "deliver"],
        help="실행 모드: full | collect | finalize | brief | deliver",
    )
    parser.add_argument(
        "--date",
        dest="briefing_date",
        default="",
        help="finalize/brief/deliver 대상 브리핑 날짜 (YYYY-MM-DD)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(validate_naver=args.mode in ("full", "collect"))

    # main 프로세스 수준 락 (collect/finalize/full 공통)
    lock_path = os.environ.get("PIPELINE_LOCK_FILE", "/tmp/news_main_pipeline.lock")
    lock_handle = acquire_process_lock(lock_path)
    if lock_handle is None:
        logging.warning(f"이미 실행 중인 파이프라인이 있어 종료합니다. lock={lock_path}")
        sys.exit(0)

    try:
        if args.mode == "collect":
            run_collect_mode(config)
        elif args.mode == "finalize":
            run_finalize_mode(config, briefing_date=args.briefing_date.strip())
        elif args.mode == "brief":
            run_brief_mode(briefing_date=args.briefing_date.strip())
        elif args.mode == "deliver":
            run_deliver_mode(briefing_date=args.briefing_date.strip())
        else:
            run_full_mode(config)
    finally:
        try:
            lock_handle.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
