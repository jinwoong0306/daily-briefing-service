"""
Supabase 적재 유틸리티

통합 크롤러(unified_crawler.py)의 기사 결과를
Supabase public.articles 테이블에 upsert 합니다.
"""

import logging
import os
import warnings
from datetime import datetime, timedelta
from typing import Optional

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

from dateutil import parser as date_parser
import pytz

try:
    from supabase import Client, create_client
except ImportError:
    Client = None
    create_client = None


def _load_env_if_exists() -> None:
    """python-dotenv 없이 .env 파일을 간단히 로드합니다."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip("'").strip('"')
    except Exception as e:
        logging.warning(f".env 로드 중 경고: {e}")


def _normalize_pub_date(pub_date: str) -> Optional[str]:
    """
    기사 발행일 문자열을 ISO-8601 문자열로 정규화합니다.
    파싱 실패 시 None을 반환합니다.
    """
    if not pub_date:
        return None

    try:
        dt = date_parser.parse(pub_date)
        return dt.isoformat()
    except Exception:
        return None


def _build_article_rows(news_list: list[dict]) -> list[dict]:
    """크롤러 기사 형식을 Supabase rows 형식으로 변환합니다."""
    rows = []

    for news in news_list:
        url = news.get("link", "").strip()
        title = news.get("title", "").strip()
        if not url or not title:
            continue

        pub_date = _normalize_pub_date(news.get("pubDate", "").strip())
        if pub_date is None:
            # filtered_news 단계에서 대부분 유효하지만, 안전하게 현재 시각으로 대체
            pub_date = datetime.utcnow().isoformat()

        rows.append(
            {
                "keyword": news.get("keyword", "기타"),
                "source_type": news.get("source_type", "unknown"),
                "title": title,
                "content": news.get("fullText", "") or "",
                "url": url,
                "pub_date": pub_date,
            }
        )

    return rows


def get_supabase_client() -> Optional["Client"]:
    """Supabase 클라이언트를 생성해서 반환합니다."""
    _load_env_if_exists()

    if create_client is None:
        logging.warning("supabase 패키지가 없어 DB 업로드를 건너뜁니다. (pip install supabase)")
        return None

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not supabase_url or not supabase_key:
        return None

    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        logging.error(f"Supabase 클라이언트 생성 실패: {e}")
        return None


def fetch_user_keywords_from_supabase(table_name: str = "user_keywords") -> list[str]:
    """
    Supabase user_keywords 테이블에서 크롤링 대상 keyword 목록을 가져옵니다.
    """
    client = get_supabase_client()
    if not client:
        return []

    try:
        res = client.table(table_name).select("keyword").execute()
        rows = res.data or []
    except Exception as e:
        logging.warning(f"Supabase user_keywords 조회 실패: {e}")
        return []

    keywords = []
    seen = set()
    for row in rows:
        keyword = str(row.get("keyword", "")).strip()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        keywords.append(keyword)

    return keywords


def fetch_user_keyword_subscriptions(table_name: str = "user_keywords") -> list[dict]:
    """
    Read user_id/keyword pairs for personalized briefing generation.
    Duplicate (user_id, keyword) rows are removed in memory.
    """
    client = get_supabase_client()
    if not client:
        return []

    try:
        res = client.table(table_name).select("user_id, keyword").execute()
        rows = res.data or []
    except Exception as e:
        logging.warning(f"Supabase user_keywords subscription query failed: {e}")
        return []

    subscriptions = []
    seen = set()
    for row in rows:
        user_id = str(row.get("user_id", "")).strip()
        keyword = str(row.get("keyword", "")).strip()
        if not user_id or not keyword:
            continue
        key = (user_id, keyword)
        if key in seen:
            continue
        seen.add(key)
        subscriptions.append({"user_id": user_id, "keyword": keyword})

    return subscriptions


def upload_articles_to_supabase(news_list: list[dict], batch_size: int = 200) -> dict:
    """
    기사 목록을 Supabase에 upsert 합니다.

    환경변수:
      - SUPABASE_URL
      - SUPABASE_SERVICE_ROLE_KEY
      - SUPABASE_ARTICLES_TABLE (기본: articles)
      - SUPABASE_ARTICLES_CONFLICT_COL (기본: url)
    """
    client = get_supabase_client()
    if not client:
        return {"enabled": False, "uploaded": 0, "prepared": 0}

    rows = _build_article_rows(news_list)
    if not rows:
        return {"enabled": True, "uploaded": 0, "prepared": 0}

    table_name = os.environ.get("SUPABASE_ARTICLES_TABLE", "articles").strip() or "articles"
    conflict_col = os.environ.get("SUPABASE_ARTICLES_CONFLICT_COL", "url").strip() or "url"

    uploaded = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.table(table_name).upsert(batch, on_conflict=conflict_col).execute()
        uploaded += len(batch)

    return {"enabled": True, "uploaded": uploaded, "prepared": len(rows)}


def _build_clustered_rows(grouped_result: dict[str, list[dict]]) -> list[dict]:
    """clustered_result.json 형태를 Supabase rows 형식으로 변환합니다."""
    rows = []

    for keyword, items in grouped_result.items():
        for item in items:
            url = item.get("link", "").strip()
            title = item.get("title", "").strip()
            if not url or not title:
                continue

            pub_date = _normalize_pub_date(item.get("pubDate", "").strip())
            if pub_date is None:
                pub_date = datetime.utcnow().isoformat()

            rows.append(
                {
                    "keyword": item.get("keyword", keyword) or keyword,
                    "source_type": item.get("source", "").strip() or "unknown",
                    "title": title,
                    "content": item.get("content", "") or "",
                    "url": url,
                    "pub_date": pub_date,
                }
            )

    return rows


def upload_clustered_result_to_supabase(grouped_result: dict[str, list[dict]], batch_size: int = 200) -> dict:
    """
    clustered_result.json 결과를 Supabase에 upsert 합니다.

    환경변수:
      - SUPABASE_URL
      - SUPABASE_SERVICE_ROLE_KEY
      - SUPABASE_CLUSTERED_TABLE (기본: SUPABASE_ARTICLES_TABLE 또는 articles)
      - SUPABASE_CLUSTERED_CONFLICT_COL (기본: url)
    """
    client = get_supabase_client()
    if not client:
        return {"enabled": False, "uploaded": 0, "prepared": 0}

    rows = _build_clustered_rows(grouped_result)
    if not rows:
        return {"enabled": True, "uploaded": 0, "prepared": 0}

    default_table = os.environ.get("SUPABASE_ARTICLES_TABLE", "articles").strip() or "articles"
    table_name = os.environ.get("SUPABASE_CLUSTERED_TABLE", default_table).strip() or default_table
    conflict_col = os.environ.get("SUPABASE_CLUSTERED_CONFLICT_COL", "url").strip() or "url"

    uploaded = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.table(table_name).upsert(batch, on_conflict=conflict_col).execute()
        uploaded += len(batch)

    return {"enabled": True, "uploaded": uploaded, "prepared": len(rows), "table": table_name}


def get_last_success_window_end(pipeline_name: str = "unified_crawler") -> Optional[datetime]:
    """
    pipeline_runs 테이블에서 마지막 성공 실행의 window_end를 반환합니다.
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        res = (
            client.table("pipeline_runs")
            .select("window_end")
            .eq("pipeline_name", pipeline_name)
            .eq("status", "success")
            .order("window_end", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        return date_parser.parse(rows[0]["window_end"])
    except Exception as e:
        logging.warning(f"pipeline_runs 조회 실패(없으면 무시): {e}")
        return None


def start_pipeline_run(pipeline_name: str, window_start: datetime, window_end: datetime) -> Optional[int]:
    """
    pipeline_runs에 running 상태를 기록하고 run id를 반환합니다.
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        payload = {
            "pipeline_name": pipeline_name,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "status": "running",
        }
        res = client.table("pipeline_runs").insert(payload).execute()
        rows = res.data or []
        if not rows:
            return None
        return rows[0].get("id")
    except Exception as e:
        logging.warning(f"pipeline_runs 시작 기록 실패(없으면 무시): {e}")
        return None


def finish_pipeline_run(run_id: Optional[int], status: str, error_message: str = "") -> None:
    """
    pipeline_runs 상태를 success/failed로 종료 업데이트합니다.
    """
    if not run_id:
        return

    client = get_supabase_client()
    if not client:
        return

    try:
        update_payload = {
            "status": status,
            "finished_at": datetime.utcnow().isoformat(),
            "error_message": error_message[:2000] if error_message else None,
        }
        client.table("pipeline_runs").update(update_payload).eq("id", run_id).execute()
    except Exception as e:
        logging.warning(f"pipeline_runs 종료 기록 실패(없으면 무시): {e}")


def get_incremental_window_kst(
    pipeline_name: str = "unified_crawler",
    overlap_minutes: int = 10,
    start_hour: int = 20,
    end_hour: int = 6,
) -> tuple[datetime, datetime, bool]:
    """
    KST 기준 증분 수집 시간창을 계산합니다.

    Returns:
      (window_start_kst, window_end_kst, used_last_success)
    """
    kst = pytz.timezone("Asia/Seoul")
    now_kst = datetime.now(kst)
    last_success_end = get_last_success_window_end(pipeline_name)

    if last_success_end is not None:
        if last_success_end.tzinfo is None:
            last_success_end = kst.localize(last_success_end)
        else:
            last_success_end = last_success_end.astimezone(kst)
        window_start = last_success_end - timedelta(minutes=max(0, overlap_minutes))
        return window_start, now_kst, True

    # 최초 실행 fallback:
    # - start_hour(기본 20) 이후: 다음 브리핑용 시작 시각
    # - end_hour(기본 06) 이전(포함): 전날 start_hour
    # - 그 외 시간: 최근 2시간
    if now_kst.hour >= start_hour:
        window_start = now_kst.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    elif now_kst.hour <= end_hour:
        window_start = (now_kst - timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
    else:
        window_start = now_kst - timedelta(hours=2)

    return window_start, now_kst, False
