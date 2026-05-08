"""
통합 뉴스 크롤링 파이프라인 (Unified News Crawler)
여러 개의 키워드로 3가지 데이터 소스를 통합 수집하고 중복 제거 후 본문을 스크래핑합니다.
"""

import os
import json
import time
import sys
import logging
import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

import requests
import feedparser
from urllib.parse import quote
import pytz
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import Optional, Tuple

# 앞서 만든 강력한 스크래퍼 재활용 (없으면 단순 BS4 폴백)
try:
    from scraper import NaverNewsScraper
except ImportError:
    NaverNewsScraper = None

try:
    from supabase_uploader import (
        upload_articles_to_supabase,
        get_incremental_window_kst,
        start_pipeline_run,
        finish_pipeline_run,
    )
except ImportError:
    upload_articles_to_supabase = None
    get_incremental_window_kst = None
    start_pipeline_run = None
    finish_pipeline_run = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _get_article_fetch_timeout() -> tuple:
    """기사 본문 요청의 연결/읽기 타임아웃을 환경변수로 조정합니다."""
    try:
        connect_timeout = float(os.environ.get("ARTICLE_FETCH_CONNECT_TIMEOUT", "3"))
        read_timeout = float(os.environ.get("ARTICLE_FETCH_READ_TIMEOUT", "7"))
    except ValueError:
        connect_timeout = 3.0
        read_timeout = 7.0
    return (connect_timeout, read_timeout)


def fetch_google_top() -> list[dict]:
    """[소스 A] 구글 종합 주요 뉴스 RSS (키워드 없이 핫이슈 수집)"""
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    logging.info(f"소스 A (Google_Top) 수집 요청: {url}")

    results = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            results.append({
                "title": entry.title,
                "link": entry.link,
                "pubDate": entry.published if hasattr(entry, "published") else "",
                "source_type": "Google_Top"
            })
    except Exception as e:
        logging.error(f"Google_Top RSS 파싱 실패: {e}")

    logging.info(f"Google_Top: {len(results)}건 수집 완료")
    return results


def fetch_google_keyword(keyword: str) -> list[dict]:
    """[소스 B] 구글 키워드 검색 뉴스 RSS"""
    encoded_keyword = quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    logging.info(f"소스 B (Google_Keyword) 수집 요청 (키워드: {keyword})")

    results = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            results.append({
                "title": entry.title,
                "link": entry.link,
                "pubDate": entry.published if hasattr(entry, "published") else "",
                "source_type": "Google_Keyword"
            })
    except Exception as e:
        logging.error(f"Google_Keyword RSS 파싱 실패: {e}")

    logging.info(f"Google_Keyword: {len(results)}건 수집 완료")
    return results


def fetch_naver_sim(keyword: str) -> list[dict]:
    """[소스 C] 네이버 뉴스 검색 API (정확도순)"""
    logging.info(f"소스 C (Naver_Sim) 수집 요청 (키워드: {keyword})")

    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")

    # 환경변수에 없으면 config.json에서 가져오기 시도
    if not client_id or not client_secret:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                api_keys = config.get("api", {})
                client_id = api_keys.get("client_id")
                client_secret = api_keys.get("client_secret")
        except:
            pass

    if not client_id or not client_secret:
        logging.error("Naver API Key(client_id, client_secret)가 없습니다. 네이버 수집을 건너뜁니다.")
        return []

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": keyword,
        "display": 50,  # 최대 100까지 가능하나 너무 많으면 스크래핑 시 오래 걸림
        "sort": "sim"   # 정확도순 정렬 (요구사항 필수 지정)
    }

    results = []
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        import re
        for item in data.get("items", []):
            title = re.sub(r'<[^>]+>', '', item.get("title", "")) # <b> 태그 제거
            # 네이버 API는 originallink와 link를 제공 (originallink가 구글과 호환성에 좋음)
            link = item.get("originallink", "") or item.get("link", "")
            results.append({
                "title": title,
                "link": link,
                "pubDate": item.get("pubDate", ""),
                "source_type": "Naver_Sim"
            })
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logging.error("네이버 API 한도 초과(429) 발생! 데이터를 덜 수집합니다.")
        else:
            logging.error(f"네이버 API HTTP 에러: {e}")
    except Exception as e:
        logging.error(f"네이버 API 호출 실패: {e}")

    logging.info(f"Naver_Sim: {len(results)}건 수집 완료")
    return results


def deduplicate_news(news_list: list[dict]) -> list[dict]:
    """
    [중복 기사 제거]
    3개의 소스에서 합쳐진 기사 중, 원본 URL(link)이나 제목(title)이 완전히 동일하면 제거합니다.
    """
    seen_links = set()
    seen_titles = set()
    deduped = []

    for news in news_list:
        link = news.get("link", "").strip()
        title = news.get("title", "").strip()

        # 유효하지 않은 데이터 건너뛰기
        if not link or not title:
            continue

        if link not in seen_links and title not in seen_titles:
            seen_links.add(link)
            seen_titles.add(title)
            deduped.append(news)

    logging.info(f"✨ 중복 제거 결과: 수집된 전체 {len(news_list)}건 -> {len(deduped)}건 ({(len(news_list) - len(deduped))}건 중복 제거됨)")
    return deduped


def filter_by_time_window(news_list: list[dict], start_dt: datetime, end_dt: datetime) -> list[dict]:
    """
    [시간 필터링]
    전달받은 시간창(start_dt ~ end_dt, KST 기준)에 발행된 기사만 통과시킵니다.
    """
    kst = pytz.timezone('Asia/Seoul')

    filtered = []
    for news in news_list:
        pub_date_str = news.get("pubDate", "").strip()
        if not pub_date_str:
            continue

        try:
            # RSS 포맷(RFC 2822), API 포맷 등 다양한 문자열을 안전하게 파싱
            dt = date_parser.parse(pub_date_str)

            # 시간대(TZ) 정보가 없으면 KST로 간주, 있으면 KST로 변환
            if dt.tzinfo is None:
                dt = kst.localize(dt)
            else:
                dt = dt.astimezone(kst)

            # 조건: 전달받은 증분 시간창(start_dt ~ end_dt) 사이에 발행된 기사
            if start_dt <= dt <= end_dt:
                filtered.append(news)
        except Exception:
            # 날짜 파싱이 불가능한 쓰레기 데이터는 조용히 무시(Drop)
            continue

    return filtered


def extract_full_text(news_list: list[dict]) -> list[dict]:
    """
    [본문 추출 및 예외 처리]
    스크래퍼의 3-Tier 폴백을 활용해 기사를 추출하되, 에러 발생 시 방어 로직으로 대응하며 실패한 기사는 통과하고 계속 진행됩니다.
    """
    logging.info(f"총 {len(news_list)}건에 대한 통합 본문 스크래핑을 시작합니다...")

    # 강력한 성능을 내는 기존 모듈 재사용
    article_timeout = _get_article_fetch_timeout()
    scraper = NaverNewsScraper(delay=0.1, timeout=article_timeout) if NaverNewsScraper else None
    if not scraper:
        logging.warning("scraper.py를 찾지 못했습니다. 단순 BeautifulSoup 방식을 사용합니다.")

    final_list = []

    for idx, news in enumerate(news_list):
        link = news["link"]
        title = news.get("title", "")
        source_type = news.get("source_type", "unknown")
        started_at = time.time()
        logging.info(
            "본문 스크래핑 진행: "
            f"{idx + 1}/{len(news_list)} [{source_type}] {title[:80]}"
        )
        try:
            full_text = None
            if scraper:
                # 구글 리다이렉션 해결 및 CSS선택자/휴리스틱 추출 활용
                full_text = scraper.scrape_article(link)
            else:
                # Fallback: bs4 단독 추출
                resp = requests.get(link, timeout=article_timeout)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.content, "lxml")
                paragraphs = soup.find_all("p")
                full_text = "\n".join([p.get_text(separator=" ", strip=True) for p in paragraphs])

            # 본문 추출이 실패했거나 너무 짧으면 빈 텍스트로 치환
            news["fullText"] = full_text if full_text else ""
            elapsed = time.time() - started_at
            if news["fullText"].strip():
                logging.info(f"본문 추출 성공: {len(news['fullText'])}자 ({elapsed:.1f}s)")
            else:
                logging.info(f"본문 추출 실패 또는 빈 본문: 다음 기사로 진행 ({elapsed:.1f}s)")
            final_list.append(news)

        except Exception as e:
            # 타임아웃, 예기치 않은 파싱 에러 등으로 프로그램이 뻗지 않도록 무조건 넘깁니다.
            elapsed = time.time() - started_at
            logging.error(f"\n[{source_type}] 본문 추출 예외 발생 (건너뜀, {elapsed:.1f}s) - '{title}': {e}")
            news["fullText"] = ""
            final_list.append(news)
            continue

    # 본문 추출 성공 통계
    success_count = sum(1 for n in final_list if n.get("fullText", "").strip())
    logging.info(f"본문 스크래핑 100% 완료! ({success_count}/{len(final_list)}건 추출 성공)")

    return final_list


def filter_articles_with_full_text(news_list: list[dict]) -> list[dict]:
    """
    본문(fullText)이 비어 있거나 공백뿐인 기사를 제거합니다.
    """
    filtered = []
    for news in news_list:
        full_text = news.get("fullText", "")
        if isinstance(full_text, str) and full_text.strip():
            filtered.append(news)
    return filtered


def acquire_process_lock(lock_path: str):
    """
    동일 서버에서 배치가 중복 실행되는 것을 방지하기 위한 파일 락.
    락 획득 실패 시 None 반환.
    """
    try:
        import fcntl
    except ImportError:
        # Windows 등 fcntl 미지원 환경은 락 없이 진행
        logging.warning("fcntl 미지원 환경입니다. 프로세스 락 없이 실행합니다.")
        return None

    lock_file = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        return lock_file
    except BlockingIOError:
        lock_file.close()
        return None


def run_pipeline(
    keywords: list[str],
    pipeline_name: Optional[str] = None,
    overlap_minutes: Optional[int] = None,
    explicit_window: Optional[Tuple[datetime, datetime]] = None,
    out_path: Optional[str] = "cache/crawled_merged_news.json",
    upload_to_db: bool = True,
    record_run: bool = True,
) -> dict:
    """여러 지정한 키워드로 통합 파이프라인을 실행합니다."""
    logging.info("=" * 60)
    logging.info(f"🚀 핵심 뉴스 통합 크롤링 묶음 파이프라인 시작 (키워드: {', '.join(keywords)})")
    logging.info("=" * 60)

    pipeline_name = (
        pipeline_name
        or os.environ.get("PIPELINE_NAME", "unified_crawler").strip()
        or "unified_crawler"
    )
    if overlap_minutes is None:
        overlap_minutes = int(os.environ.get("PIPELINE_WINDOW_OVERLAP_MINUTES", "10"))

    start_hour = int(os.environ.get("PIPELINE_COLLECTION_START_HOUR", "20"))
    end_hour = int(os.environ.get("PIPELINE_COLLECTION_END_HOUR", "6"))
    kst = pytz.timezone("Asia/Seoul")

    # A) 시간창 계산 (명시값 > 증분 계산)
    if explicit_window is not None:
        window_start, window_end = explicit_window
        if window_start.tzinfo is None:
            window_start = kst.localize(window_start)
        else:
            window_start = window_start.astimezone(kst)
        if window_end.tzinfo is None:
            window_end = kst.localize(window_end)
        else:
            window_end = window_end.astimezone(kst)
        used_last_success = False
        window_source = "explicit"
    elif get_incremental_window_kst is not None:
        window_start, window_end, used_last_success = get_incremental_window_kst(
            pipeline_name=pipeline_name,
            overlap_minutes=overlap_minutes,
            start_hour=start_hour,
            end_hour=end_hour,
        )
        window_source = "last_success" if used_last_success else "fallback"
    else:
        now_kst = datetime.now(kst)
        if now_kst.hour >= start_hour:
            window_start = now_kst.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        elif now_kst.hour <= end_hour:
            window_start = (now_kst - timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
        else:
            window_start = now_kst - timedelta(hours=2)
        window_end = now_kst
        used_last_success = False
        window_source = "fallback_no_supabase"

    logging.info(
        "🕒 수집 시간창(KST): "
        f"{window_start.isoformat()} ~ {window_end.isoformat()} "
        f"(기준: {window_source})"
    )

    run_id = None
    if record_run and start_pipeline_run is not None:
        run_id = start_pipeline_run(
            pipeline_name=pipeline_name,
            window_start=window_start.astimezone(pytz.UTC),
            window_end=window_end.astimezone(pytz.UTC),
        )
        if run_id:
            logging.info(f"🧾 pipeline_runs 시작 기록: run_id={run_id}")

    try:
        # 1. 공통 키워드 무관 소스 (Google Top RSS)
        all_news = fetch_google_top()
        # Google Top 뉴스는 특정 키워드가 없으므로 '주요이슈'로 지정
        for news in all_news:
            news["keyword"] = "주요이슈"

        # 2. 키워드별 소스 수집
        for kw in keywords:
            logging.info(f"\n--- [키워드: {kw}] 수집 시작 ---")
            kw_news = fetch_google_keyword(kw)
            nv_news = fetch_naver_sim(kw)

            # 기사별 키워드 메타데이터 부착 (클러스터링 시 분류용)
            for n in kw_news:
                n["keyword"] = kw
            for n in nv_news:
                n["keyword"] = kw

            all_news.extend(kw_news)
            all_news.extend(nv_news)

        logging.info(f"\n총 긁어온 원본 기사 수: {len(all_news)}건")

        # 3. 중복 기사 필터링 (URL 또는 제목이 같으면 제거)
        deduped_news = deduplicate_news(all_news)

        # 4. 발행일시 기준 증분 시간 필터링
        filtered_news = filter_by_time_window(deduped_news, window_start, window_end)

        # 5. 로그 요약
        logging.info(
            "✅ 3개 소스에서 총 "
            f"{len(all_news)}개 기사 수집 -> 중복 제거 후 {len(deduped_news)}개 "
            f"-> 시간 필터링 통과 {len(filtered_news)}개 -> 본문 스크래핑 시작"
        )

        # 6. 본문 텍스트 추출 (스크래핑)
        final_news = extract_full_text(filtered_news)

        # 7. 본문이 없는 기사 제거 (최종 merged 결과 정제)
        final_news_with_text = filter_articles_with_full_text(final_news)
        dropped_count = len(final_news) - len(final_news_with_text)
        logging.info(
            "🧹 본문 기준 정제 완료: "
            f"{len(final_news)}건 -> {len(final_news_with_text)}건 "
            f"({dropped_count}건 제거)"
        )

        final_data = {
            "meta": {
                "source": "unified_pipeline",
                "keywords": keywords,
                "description": "다중 키워드로 수집된 통합 뉴스 데이터",
                "window_start_kst": window_start.isoformat(),
                "window_end_kst": window_end.isoformat(),
                "window_source": window_source,
            },
            "articles": final_news_with_text,
        }

        # 8. 결과 캐시 저장 (옵션)
        if out_path:
            out_dir = os.path.dirname(out_path) or "."
            os.makedirs(out_dir, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            logging.info(
                f"💾 파이프라인 데이터 구축 최종 완료! \n"
                f"전체 {len(final_news_with_text)}건의 데이터가 '{out_path}'에 저장되었습니다."
            )
        else:
            logging.info("💾 out_path 미지정으로 파일 저장은 건너뜁니다.")

        # 9. Supabase 업로드 (옵션)
        if upload_to_db:
            if upload_articles_to_supabase is None:
                logging.warning("supabase_uploader 모듈을 찾지 못해 DB 업로드를 건너뜁니다.")
            else:
                upload_result = upload_articles_to_supabase(final_news_with_text)
                if upload_result.get("enabled"):
                    logging.info(
                        "🗄️ Supabase 업로드 완료: "
                        f"{upload_result.get('uploaded', 0)}건 "
                        f"(준비된 row: {upload_result.get('prepared', 0)}건)"
                    )
                else:
                    logging.info(
                        "ℹ️ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY가 없어 "
                        "DB 업로드를 건너뜁니다."
                    )
        else:
            logging.info("🗄️ 이번 실행은 upload_to_db=False 설정으로 DB 업로드를 건너뜁니다.")

        if record_run and finish_pipeline_run is not None:
            finish_pipeline_run(run_id=run_id, status="success")

        return final_data

    except Exception as e:
        logging.exception(f"파이프라인 실행 실패: {e}")
        if record_run and finish_pipeline_run is not None:
            finish_pipeline_run(run_id=run_id, status="failed", error_message=str(e))
        raise


if __name__ == "__main__":
    # config.json에서 키워드 리스트를 읽어옵니다.
    target_keywords = ["인공지능", "반도체"] # 기본값
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if "keywords" in cfg:
                target_keywords = cfg["keywords"]
    except:
        pass

    lock_path = os.environ.get("PIPELINE_LOCK_FILE", "/tmp/news_pipeline.lock")
    lock_handle = acquire_process_lock(lock_path)
    if lock_handle is None:
        logging.warning(f"이미 실행 중인 파이프라인이 있어 종료합니다. lock={lock_path}")
        sys.exit(0)

    try:
        run_pipeline(target_keywords)
    finally:
        try:
            lock_handle.close()
        except Exception:
            pass
