"""
야간 수집 누적(staging) 데이터 관리 모듈

목적:
- 20:00~06:00 사이 2시간 간격 수집 결과를 briefing_date 단위로 누적 저장
- 06:10 최종 처리 시 누적 데이터 전체를 클러스터링 대상으로 사용
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional

import pytz


KST = pytz.timezone("Asia/Seoul")


def resolve_briefing_date_for_collection(
    ref_dt: Optional[datetime] = None,
    start_hour: int = 20,
    end_hour: int = 6,
) -> str:
    """
    수집 시점 기준 briefing_date(YYYY-MM-DD)를 계산합니다.

    예:
    - 2026-04-04 20:00 -> briefing_date=2026-04-05
    - 2026-04-05 02:00 -> briefing_date=2026-04-05
    """
    dt = ref_dt or datetime.now(KST)
    if dt.tzinfo is None:
        dt = KST.localize(dt)
    else:
        dt = dt.astimezone(KST)

    if dt.hour >= start_hour:
        target = (dt + timedelta(days=1)).date()
    elif dt.hour <= end_hour:
        target = dt.date()
    else:
        # 수집 시간대 밖 수동 실행 시에는 당일 브리핑 날짜로 처리
        target = dt.date()
    return target.isoformat()


def resolve_briefing_date_for_finalize(ref_dt: Optional[datetime] = None) -> str:
    """
    최종 처리 시 기본 briefing_date를 계산합니다.
    기본값은 KST 기준 '오늘'입니다.
    """
    dt = ref_dt or datetime.now(KST)
    if dt.tzinfo is None:
        dt = KST.localize(dt)
    else:
        dt = dt.astimezone(KST)
    return dt.date().isoformat()


def get_staging_path(briefing_date: str, staging_dir: str = "cache/staging") -> str:
    return os.path.join(staging_dir, f"{briefing_date}.json")


def _default_staging_payload(briefing_date: str) -> dict:
    now = datetime.now(KST).isoformat()
    return {
        "meta": {
            "briefing_date": briefing_date,
            "collection_window_kst": "20:00-06:00",
            "created_at": now,
            "updated_at": now,
            "finalized_at": None,
        },
        "runs": [],
        "articles": [],
    }


def load_staging(briefing_date: str, staging_dir: str = "cache/staging") -> dict:
    path = get_staging_path(briefing_date, staging_dir)
    if not os.path.exists(path):
        return _default_staging_payload(briefing_date)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "meta" not in data:
        data["meta"] = {}
    data["meta"].setdefault("briefing_date", briefing_date)
    data.setdefault("runs", [])
    data.setdefault("articles", [])
    return data


def _normalize_title(title: str) -> str:
    return " ".join((title or "").lower().split())


def _article_key(article: dict) -> str:
    url = (article.get("link") or article.get("url") or "").strip()
    if url:
        return f"url:{url}"

    title = _normalize_title(article.get("title", ""))
    pub_date = (article.get("pubDate") or article.get("pub_date") or "").strip()
    source = (article.get("source_type") or article.get("source") or "").strip()
    return f"title:{title}|pub:{pub_date}|source:{source}"


def _merge_article(old: dict, new: dict) -> tuple[dict, bool]:
    """
    두 기사 레코드를 병합.
    Returns:
      (merged_article, replaced_with_new)
    """
    merged = dict(old)
    replaced = False

    old_text = (old.get("fullText") or old.get("content") or "").strip()
    new_text = (new.get("fullText") or new.get("content") or "").strip()

    # 본문이 더 긴 쪽을 우선
    if len(new_text) > len(old_text):
        merged.update(new)
        replaced = True
    else:
        # 본문이 짧으면 핵심 필드 중 빈 값만 보완
        for k, v in new.items():
            if k not in merged or merged[k] in ("", None):
                merged[k] = v

    return merged, replaced


def append_articles_to_staging(
    briefing_date: str,
    new_articles: list[dict],
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
    staging_dir: str = "cache/staging",
) -> dict:
    """
    새 수집 기사 목록을 briefing_date staging 파일에 누적 저장합니다.
    """
    os.makedirs(staging_dir, exist_ok=True)
    data = load_staging(briefing_date, staging_dir)

    existing_map = {}
    for article in data.get("articles", []):
        existing_map[_article_key(article)] = article

    added_count = 0
    updated_count = 0
    for article in new_articles:
        key = _article_key(article)
        if key in existing_map:
            merged, replaced = _merge_article(existing_map[key], article)
            existing_map[key] = merged
            if replaced:
                updated_count += 1
        else:
            existing_map[key] = article
            added_count += 1

    merged_articles = list(existing_map.values())

    now_kst = datetime.now(KST).isoformat()
    run_entry = {
        "collected_at_kst": now_kst,
        "incoming_count": len(new_articles),
        "added_count": added_count,
        "updated_count": updated_count,
        "total_after_merge": len(merged_articles),
    }
    if window_start is not None:
        run_entry["window_start_kst"] = window_start.isoformat()
    if window_end is not None:
        run_entry["window_end_kst"] = window_end.isoformat()

    data["runs"].append(run_entry)
    data["articles"] = merged_articles
    data["meta"]["updated_at"] = now_kst
    data["meta"]["briefing_date"] = briefing_date
    data["meta"].setdefault("collection_window_kst", "20:00-06:00")

    path = get_staging_path(briefing_date, staging_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "path": path,
        "incoming_count": len(new_articles),
        "added_count": added_count,
        "updated_count": updated_count,
        "total_after_merge": len(merged_articles),
    }


def mark_staging_finalized(
    briefing_date: str,
    staging_dir: str = "cache/staging",
    archive_copy: bool = True,
) -> dict:
    """
    staging 파일에 finalized_at을 기록하고, 필요시 archive 사본을 생성합니다.
    """
    path = get_staging_path(briefing_date, staging_dir)
    if not os.path.exists(path):
        return {"path": path, "archived_path": None, "exists": False}

    data = load_staging(briefing_date, staging_dir)
    now_kst = datetime.now(KST).isoformat()
    data["meta"]["finalized_at"] = now_kst
    data["meta"]["updated_at"] = now_kst

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    archived_path = None
    if archive_copy:
        archive_dir = os.path.join(staging_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        ts = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
        archived_path = os.path.join(archive_dir, f"{briefing_date}_{ts}.json")
        shutil.copy2(path, archived_path)

    return {"path": path, "archived_path": archived_path, "exists": True}
