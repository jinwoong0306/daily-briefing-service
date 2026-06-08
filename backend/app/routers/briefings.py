from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.dependencies import get_current_user
from app.models import User, UserArticleFeedback, UserSavedArticle
from app.schemas import (
    BriefingActionResponse,
    BriefingBookmarksResponse,
    BriefingFeedbackRequest,
    BriefingGroupedKeywordItemResponse,
    BriefingGroupedKeywordResponse,
    BriefingItemResponse,
    BriefingsTodayGroupedResponse,
    BriefingsTodayResponse,
)

router = APIRouter(prefix="/briefings", tags=["briefings"])
settings = get_settings()
logger = logging.getLogger("uvicorn.error")

_FALLBACK_IMAGE_URL = (
    "https://images.unsplash.com/photo-1504711434969-e33886168f5c"
    "?auto=format&fit=crop&w=1200&q=80"
)


def _redis_client() -> Redis:
    redis_url = (settings.redis_url or "").strip()
    if not redis_url:
        raise RedisError("REDIS_URL is not configured")
    if redis_url.startswith("redis://") and ".upstash.io" in redis_url:
        redis_url = "rediss://" + redis_url[len("redis://") :]
    return Redis.from_url(redis_url, decode_responses=True)


def _table_name(name: str, db: Session) -> str:
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        return name
    return f"public.{name}"


def _normalized_category_sql(column: str) -> str:
    value = f"lower(trim(coalesce({column}, '')))"
    return f"""
    case
      when {value} in ('it/과학', 'it', '과학', 'science', 'tech', 'technology', 'ai', '인공지능') then 'IT/과학'
      when {value} in ('경제', 'economy', 'business', 'finance', 'financial', 'market', '금융') then '경제'
      when {value} in ('정치', 'politics', 'policy', 'government', '국회') then '정치'
      when {value} in ('엔터테인먼트', 'entertainment', '연예') then '엔터테인먼트'
      when {value} in ('스포츠', 'sports', 'sport', '축구', '야구', '농구', '배구') then '스포츠'
      when {value} in ('헬스', 'health', 'medical', 'wellness', '건강', '의료', '헬스케어', 'healthcare', 'health-care', '웰빙', '바이오', '질병') then '헬스'
      when {value} in ('아트&컬처', '아트', '컬처', 'art', 'arts', 'culture') then '아트&컬처'
      when {value} in (
        '월드 뉴스', 'world news', 'world', 'international', 'global', '해외',
        '월드뉴스', 'worldnews', 'world_news', '국제', '국제뉴스', '글로벌', '해외뉴스'
      ) then '월드 뉴스'
      else nullif(trim(coalesce({column}, '')), '')
    end
    """


def _canonical_category_label(raw: str | None) -> str:
    """DB `user_keywords`와 Redis 묶음 블록의 `keyword`를 동일 축으로 맞출 때 사용."""
    if raw is None:
        return ""
    trimmed = str(raw).strip()
    if not trimmed:
        return ""
    value = trimmed.lower()
    if value in (
        "it/과학",
        "it",
        "과학",
        "science",
        "tech",
        "technology",
        "ai",
        "인공지능",
    ):
        return "IT/과학"
    if value in ("경제", "economy", "business", "finance", "financial", "market", "금융"):
        return "경제"
    if value in ("정치", "politics", "policy", "government", "국회"):
        return "정치"
    if value in ("엔터테인먼트", "entertainment", "연예"):
        return "엔터테인먼트"
    if value in ("스포츠", "sports", "sport", "축구", "야구", "농구", "배구"):
        return "스포츠"
    if value in (
        "헬스",
        "health",
        "medical",
        "wellness",
        "건강",
        "의료",
        "헬스케어",
        "healthcare",
        "health-care",
        "웰빙",
        "바이오",
        "질병",
    ):
        return "헬스"
    if value in ("아트&컬처", "아트", "컬처", "art", "arts", "culture"):
        return "아트&컬처"
    if value in (
        "월드 뉴스",
        "world news",
        "world",
        "international",
        "global",
        "해외",
        "월드뉴스",
        "worldnews",
        "world_news",
        "국제",
        "국제뉴스",
        "글로벌",
        "해외뉴스",
    ):
        return "월드 뉴스"
    return trimmed


def _filter_grouped_response_by_user_keywords(
    grouped: BriefingsTodayGroupedResponse,
    current_user: User,
    db: Session,
) -> BriefingsTodayGroupedResponse:
    """Redis 묶음 브리핑이 과거 키워드 구성으로 남아 있어도, 현재 저장된 관심 키워드만 노출."""
    keywords_table = _table_name("user_keywords", db)
    rows = db.execute(
        text(f"select keyword from {keywords_table} where user_id = :user_id"),
        {"user_id": current_user.id},
    ).scalars().all()
    if not rows:
        return grouped.model_copy(update={"user_id": str(current_user.id)})
    allowed = {_canonical_category_label(k) for k in rows if isinstance(k, str) and k.strip()}
    filtered = [
        block
        for block in grouped.keywords
        if _canonical_category_label(block.keyword) in allowed
    ]
    return BriefingsTodayGroupedResponse(
        briefing_date=grouped.briefing_date,
        user_id=str(current_user.id),
        keywords=filtered,
    )


def _build_highlights(source: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", source).strip()
    if not normalized:
        return ["핵심 내용 요약을 준비 중입니다."]

    sentences = re.split(r"(?<=[.!?])\s+|(?<=다\.)\s+", normalized)
    cleaned = [sentence.strip() for sentence in sentences if sentence.strip()]
    if not cleaned:
        return ["핵심 내용 요약을 준비 중입니다."]
    return cleaned[:3]


def _estimate_read_time(summary: str) -> int:
    length = len(summary.replace(" ", ""))
    if length <= 120:
        return 1
    return min(8, max(1, length // 220 + 1))


def _fallback_image_url(seed: str) -> str:
    safe_seed = re.sub(r"[^a-zA-Z0-9_-]", "", seed) or "briefing"
    return f"https://picsum.photos/seed/{safe_seed}/1200/675"


def _thumbnail_from_url(url: str | None, *, seed: str) -> str:
    if url:
        normalized = str(url).strip()
        if normalized:
            return f"https://image.thum.io/get/width/1200/noanimate/{normalized}"
    return _fallback_image_url(seed)


def _pick_image_url(data: dict[str, object], *, seed: str, url: str | None) -> str:
    candidates = [
        data.get("image_url"),
        data.get("imageUrl"),
        data.get("thumbnail_url"),
        data.get("thumbnailUrl"),
        data.get("thumbnail"),
        data.get("image"),
        data.get("cover_image"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        value = str(candidate).strip()
        if value:
            return value
    return _thumbnail_from_url(url, seed=seed)


def _parse_published_at(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _normalize_article_id(raw_id: object, url: str | None, title: str) -> int:
    if raw_id is not None:
        raw_text = str(raw_id).strip()
        if raw_text.isdigit():
            return int(raw_text)
    seed = (url or title or "briefing-item").strip().lower()
    hashed = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return int(hashed, 16)


def _ensure_article_row(
    *,
    db: Session,
    article_id: int,
    title: str,
    content: str,
    keyword: str,
    source_type: str,
    pub_date: datetime,
    url: str | None,
) -> None:
    articles_table = _table_name("articles", db)
    existing = db.execute(
        text(f"select 1 from {articles_table} where id = :article_id limit 1"),
        {"article_id": article_id},
    ).scalar()
    if existing:
        db.execute(
            text(
                f"""
                update {articles_table}
                set title = :title,
                    content = :content,
                    keyword = :keyword,
                    source_type = :source_type,
                    pub_date = :pub_date,
                    url = :url
                where id = :article_id
                """
            ),
            {
                "article_id": article_id,
                "title": title,
                "content": content,
                "keyword": keyword,
                "source_type": source_type,
                "pub_date": pub_date,
                "url": url,
            },
        )
        return
    db.execute(
        text(
            f"""
            insert into {articles_table}
            (id, title, content, keyword, source_type, pub_date, url)
            values (:article_id, :title, :content, :keyword, :source_type, :pub_date, :url)
            """
        ),
        {
            "article_id": article_id,
            "title": title,
            "content": content,
            "keyword": keyword,
            "source_type": source_type,
            "pub_date": pub_date,
            "url": url,
        },
    )


def _load_redis_keyword_items(current_user: User, db: Session) -> list[BriefingItemResponse]:
    if not settings.redis_url:
        return []

    keywords_table = _table_name("user_keywords", db)
    keywords = db.execute(
        text(f"select keyword from {keywords_table} where user_id = :user_id"),
        {"user_id": current_user.id},
    ).scalars().all()
    if not keywords:
        return []

    try:
        client = _redis_client()
    except RedisError as exc:
        logger.warning("Redis briefings unavailable: %s", exc)
        return []

    briefing_date = datetime.now(timezone.utc).date().isoformat()
    normalized_items: list[dict[str, object]] = []

    for keyword in keywords:
        if not isinstance(keyword, str) or not keyword.strip():
            continue
        redis_key = f"briefing:{briefing_date}:keyword:{quote(keyword.strip(), safe='')}"
        try:
            raw = client.get(redis_key)
        except RedisError as exc:
            logger.warning("Failed to read redis key=%s error=%s", redis_key, exc)
            continue
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        entries = payload.get("items")
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            url = str(entry.get("url") or "").strip() or None
            source_name = str(entry.get("source_type") or "Redis Feed").strip() or "Redis Feed"
            summary = str(entry.get("summary") or payload.get("summary") or title).strip() or title
            published_at = _parse_published_at(entry.get("pub_date"))
            article_id = _normalize_article_id(entry.get("id"), url, title)
            image_url = _pick_image_url(entry, seed=str(article_id), url=url)
            _ensure_article_row(
                db=db,
                article_id=article_id,
                title=title,
                content=summary,
                keyword=keyword.strip(),
                source_type=source_name,
                pub_date=published_at,
                url=url,
            )
            normalized_items.append(
                {
                    "id": article_id,
                    "category": keyword.strip(),
                    "title": title,
                    "summary": summary,
                    "source_name": source_name,
                    "published_at": published_at,
                    "original_url": url,
                    "image_url": image_url,
                }
            )

    if not normalized_items:
        return []

    db.commit()
    article_ids = [int(item["id"]) for item in normalized_items]
    saved_ids = set(
        db.scalars(
            select(UserSavedArticle.article_id).where(
                UserSavedArticle.user_id == current_user.id,
                UserSavedArticle.article_id.in_(article_ids),
            )
        ).all()
    )
    feedback_rows = db.execute(
        select(UserArticleFeedback.article_id, UserArticleFeedback.feedback_type).where(
            UserArticleFeedback.user_id == current_user.id,
            UserArticleFeedback.article_id.in_(article_ids),
        )
    ).all()
    feedback_by_article_id = {int(article_id): str(feedback_type) for article_id, feedback_type in feedback_rows}

    response_items = [
        BriefingItemResponse(
            id=str(int(item["id"])),
            category=str(item["category"]),
            title=str(item["title"]),
            summary=str(item["summary"]),
            highlights=_build_highlights(str(item["summary"])),
            image_url=str(item.get("image_url") or _fallback_image_url(str(item["id"]))),
            source_name=str(item["source_name"]),
            published_at=item["published_at"] if isinstance(item["published_at"], datetime) else datetime.now(timezone.utc),
            read_time_minutes=_estimate_read_time(str(item["summary"])),
            original_url=(str(item["original_url"]) if item["original_url"] else None),
            is_bookmarked=int(item["id"]) in saved_ids,
            feedback_type=feedback_by_article_id.get(int(item["id"])),
        )
        for item in normalized_items
    ]
    response_items.sort(key=lambda item: item.published_at, reverse=True)
    return response_items


def _load_redis_user_grouped(current_user: User) -> BriefingsTodayGroupedResponse | None:
    if not settings.redis_url:
        return None
    briefing_date = datetime.now(timezone.utc).date().isoformat()
    user_key = f"briefing:{briefing_date}:user:{current_user.id}"
    try:
        client = _redis_client()
        raw = client.get(user_key)
    except RedisError as exc:
        logger.warning("Failed to load redis grouped briefing key=%s error=%s", user_key, exc)
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    keywords_raw = payload.get("keywords")
    if not isinstance(keywords_raw, list):
        return None

    keywords: list[BriefingGroupedKeywordResponse] = []
    for keyword_block in keywords_raw:
        if not isinstance(keyword_block, dict):
            continue
        keyword = str(keyword_block.get("keyword") or "").strip()
        if not keyword:
            continue
        items_raw = keyword_block.get("items")
        if not isinstance(items_raw, list):
            items_raw = []
        items: list[BriefingGroupedKeywordItemResponse] = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            item_id = str(item.get("id") or "").strip() or str(
                _normalize_article_id(item.get("id"), str(item.get("url") or "").strip() or None, title)
            )
            items.append(
                BriefingGroupedKeywordItemResponse(
                    id=item_id,
                    title=title,
                    summary=str(item.get("summary") or title).strip() or title,
                    url=(str(item.get("url")).strip() if item.get("url") is not None else None),
                    image_url=_pick_image_url(
                        item,
                        seed=item_id,
                        url=(str(item.get("url")).strip() if item.get("url") else None),
                    ),
                    pub_date=_parse_published_at(item.get("pub_date")),
                    source_type=(str(item.get("source_type")).strip() if item.get("source_type") else None),
                )
            )
        keywords.append(
            BriefingGroupedKeywordResponse(
                keyword=keyword,
                headline=(str(keyword_block.get("headline")).strip() if keyword_block.get("headline") else None),
                summary=(str(keyword_block.get("summary")).strip() if keyword_block.get("summary") else None),
                items=items,
            )
        )
    return BriefingsTodayGroupedResponse(
        briefing_date=str(payload.get("briefing_date") or briefing_date),
        user_id=str(payload.get("user_id") or current_user.id),
        keywords=keywords,
    )


def _article_exists(article_id: int, db: Session) -> bool:
    table_name = _table_name("articles", db)
    exists = db.execute(
        text(f"select 1 from {table_name} where id = :article_id limit 1"),
        {"article_id": article_id},
    ).scalar()
    return bool(exists)


@router.get("/today", response_model=BriefingsTodayResponse)
def get_today_briefings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingsTodayResponse:
    redis_items = _load_redis_keyword_items(current_user=current_user, db=db)
    if redis_items:
        return BriefingsTodayResponse(items=redis_items)

    articles_table = _table_name("articles", db)
    keywords_table = _table_name("user_keywords", db)
    saved_table = _table_name("user_saved_articles", db)
    feedbacks_table = _table_name("user_article_feedbacks", db)
    normalized_article_keyword = _normalized_category_sql("a.keyword")
    normalized_user_keyword = _normalized_category_sql("uk.keyword")

    has_keywords = bool(
        db.execute(
            text(
                """
                select 1
                from {keywords_table}
                where user_id = :user_id
                limit 1
                """
                .format(
                    keywords_table=keywords_table,
                )
            ),
            {"user_id": current_user.id},
        ).scalar()
    )

    rows = db.execute(
        text(
            """
            select
              a.id,
              a.title,
              a.content,
              a.keyword,
              {normalized_article_keyword} as normalized_category,
              a.source_type,
              a.pub_date,
              a.url,
              (usa.id is not null) as is_bookmarked,
              uaf.feedback_type
            from {articles_table} a
            join {keywords_table} uk
              on {normalized_user_keyword} = {normalized_article_keyword}
            left join {saved_table} usa
              on usa.user_id = :user_id and usa.article_id = a.id
            left join {feedbacks_table} uaf
              on uaf.user_id = :user_id and uaf.article_id = a.id
            where uk.user_id = :user_id
              and a.pub_date >= :window_start
            order by a.pub_date desc
            limit 30
            """
            .format(
                articles_table=articles_table,
                keywords_table=keywords_table,
                saved_table=saved_table,
                feedbacks_table=feedbacks_table,
                normalized_user_keyword=normalized_user_keyword,
                normalized_article_keyword=normalized_article_keyword,
            )
        ),
        {
            "user_id": current_user.id,
            "window_start": datetime.now(timezone.utc) - timedelta(days=7),
        },
    ).mappings().all()

    if not rows and not has_keywords:
        rows = db.execute(
            text(
                """
                select
                  a.id,
                  a.title,
                  a.content,
                  a.keyword,
                  {normalized_article_keyword} as normalized_category,
                  a.source_type,
                  a.pub_date,
                  a.url,
                  (usa.id is not null) as is_bookmarked,
                  uaf.feedback_type
                from {articles_table} a
                left join {saved_table} usa
                  on usa.user_id = :user_id and usa.article_id = a.id
                left join {feedbacks_table} uaf
                  on uaf.user_id = :user_id and uaf.article_id = a.id
                order by a.pub_date desc
                limit 20
                """
                .format(
                    articles_table=articles_table,
                    saved_table=saved_table,
                    feedbacks_table=feedbacks_table,
                    normalized_article_keyword=normalized_article_keyword,
                )
            ),
            {"user_id": current_user.id},
        ).mappings().all()

    items: list[BriefingItemResponse] = []
    for row in rows:
        title = str(row.get("title") or "제목 없음")
        content = str(row.get("content") or "")
        summary = content.strip()[:280] if content.strip() else title
        source_name = str(row.get("source_type") or "News Source")
        category = str(row.get("normalized_category") or row.get("keyword") or "기타")
        published_at = row.get("pub_date")
        if not isinstance(published_at, datetime):
            published_at = datetime.now(timezone.utc)

        items.append(
            BriefingItemResponse(
                id=str(row.get("id")),
                category=category,
                title=title,
                summary=summary,
                highlights=_build_highlights(content if content else title),
                image_url=_thumbnail_from_url(
                    (str(row.get("url")).strip() if row.get("url") else None),
                    seed=str(row.get("id") or title),
                ),
                source_name=source_name,
                published_at=published_at,
                read_time_minutes=_estimate_read_time(summary),
                original_url=row.get("url"),
                is_bookmarked=bool(row.get("is_bookmarked")),
                feedback_type=(
                    str(row.get("feedback_type")) if row.get("feedback_type") is not None else None
                ),
            )
        )

    return BriefingsTodayResponse(items=items)


def _category_key_for_grouping(category: str) -> str:
    key = _canonical_category_label(category)
    return key if key else (str(category).strip() or "기타")


def _build_grouped_from_today_items(
    items: list[BriefingItemResponse],
    current_user: User,
    db: Session,
    briefing_date: str,
) -> BriefingsTodayGroupedResponse:
    """Redis 묶음이 없을 때 `today`와 동일한 기사 목록을 카테고리 섹션으로 변환."""
    keywords_table = _table_name("user_keywords", db)
    preferred_rows = db.execute(
        text(
            """
            select keyword from {keywords_table}
            where user_id = :user_id
            order by created_at asc
            """.format(keywords_table=keywords_table)
        ),
        {"user_id": current_user.id},
    ).scalars().all()

    by_cat: dict[str, list[BriefingItemResponse]] = {}
    for item in items:
        key = _category_key_for_grouping(item.category)
        by_cat.setdefault(key, []).append(item)

    for key in by_cat:
        by_cat[key].sort(key=lambda it: it.published_at, reverse=True)

    ordered_keys: list[str] = []
    seen: set[str] = set()
    for raw_kw in preferred_rows:
        if not isinstance(raw_kw, str) or not raw_kw.strip():
            continue
        ck = _canonical_category_label(raw_kw)
        if ck in by_cat and ck not in seen:
            ordered_keys.append(ck)
            seen.add(ck)
    for ck in sorted(by_cat.keys()):
        if ck not in seen:
            ordered_keys.append(ck)
            seen.add(ck)

    blocks: list[BriefingGroupedKeywordResponse] = []
    for cat in ordered_keys:
        cat_items = by_cat[cat]
        first = cat_items[0]
        summary_base = first.summary.strip() if first.summary.strip() else first.title
        if len(summary_base) > 300:
            summary_base = summary_base[:297].rstrip() + "..."
        if len(cat_items) > 1:
            section_summary = f"{summary_base} (관련 기사 {len(cat_items)}건)"
        else:
            section_summary = summary_base
        headline = f"{cat} 이슈 요약"

        gitems: list[BriefingGroupedKeywordItemResponse] = []
        for it in cat_items:
            gitems.append(
                BriefingGroupedKeywordItemResponse(
                    id=it.id,
                    title=it.title,
                    summary=it.summary,
                    url=it.original_url,
                    image_url=it.image_url,
                    pub_date=it.published_at,
                    source_type=it.source_name,
                )
            )
        blocks.append(
            BriefingGroupedKeywordResponse(
                keyword=cat,
                headline=headline,
                summary=section_summary,
                items=gitems,
            )
        )

    return BriefingsTodayGroupedResponse(
        briefing_date=briefing_date,
        user_id=str(current_user.id),
        keywords=blocks,
    )


@router.get("/today/grouped", response_model=BriefingsTodayGroupedResponse)
def get_today_grouped_briefings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingsTodayGroupedResponse:
    briefing_date = datetime.now(timezone.utc).date().isoformat()
    grouped = _load_redis_user_grouped(current_user=current_user)
    if grouped is not None:
        grouped = _filter_grouped_response_by_user_keywords(grouped, current_user, db)
        if grouped.keywords:
            return grouped
    today = get_today_briefings(current_user=current_user, db=db)
    if not today.items:
        return BriefingsTodayGroupedResponse(
            briefing_date=briefing_date,
            user_id=str(current_user.id),
            keywords=[],
        )
    return _build_grouped_from_today_items(today.items, current_user, db, briefing_date)


@router.post("/{article_id}/feedback", response_model=BriefingActionResponse)
def upsert_briefing_feedback(
    article_id: int,
    payload: BriefingFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingActionResponse:
    if not _article_exists(article_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    existing = db.scalar(
        select(UserArticleFeedback).where(
            UserArticleFeedback.user_id == current_user.id,
            UserArticleFeedback.article_id == article_id,
        )
    )
    if existing is None:
        db.add(
            UserArticleFeedback(
                user_id=current_user.id,
                article_id=article_id,
                feedback_type=payload.feedback_type,
            )
        )
    else:
        existing.feedback_type = payload.feedback_type
        existing.updated_at = datetime.now(timezone.utc)

    db.commit()
    return BriefingActionResponse(
        article_id=str(article_id),
        message="Feedback saved",
    )


@router.put("/{article_id}/bookmark", response_model=BriefingActionResponse)
def save_bookmark(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingActionResponse:
    if not _article_exists(article_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    existing = db.scalar(
        select(UserSavedArticle).where(
            UserSavedArticle.user_id == current_user.id,
            UserSavedArticle.article_id == article_id,
        )
    )
    if existing is None:
        db.add(UserSavedArticle(user_id=current_user.id, article_id=article_id))
        db.commit()

    return BriefingActionResponse(article_id=str(article_id), message="Bookmark saved")


@router.delete("/{article_id}/bookmark", response_model=BriefingActionResponse)
def delete_bookmark(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingActionResponse:
    if not _article_exists(article_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    db.execute(
        delete(UserSavedArticle).where(
            UserSavedArticle.user_id == current_user.id,
            UserSavedArticle.article_id == article_id,
        )
    )
    db.commit()
    return BriefingActionResponse(article_id=str(article_id), message="Bookmark removed")


@router.get("/bookmarks", response_model=BriefingBookmarksResponse)
def get_bookmarked_briefings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingBookmarksResponse:
    articles_table = _table_name("articles", db)
    saved_table = _table_name("user_saved_articles", db)
    feedbacks_table = _table_name("user_article_feedbacks", db)
    normalized_article_keyword = _normalized_category_sql("a.keyword")

    rows = db.execute(
        text(
            """
            select
              a.id,
              a.title,
              a.content,
              a.keyword,
              {normalized_article_keyword} as normalized_category,
              a.source_type,
              a.pub_date,
              a.url,
              true as is_bookmarked,
              uaf.feedback_type
            from {saved_table} usa
            join {articles_table} a
              on a.id = usa.article_id
            left join {feedbacks_table} uaf
              on uaf.user_id = usa.user_id and uaf.article_id = a.id
            where usa.user_id = :user_id
            order by usa.created_at desc
            """
            .format(
                saved_table=saved_table,
                articles_table=articles_table,
                feedbacks_table=feedbacks_table,
                normalized_article_keyword=normalized_article_keyword,
            )
        ),
        {"user_id": current_user.id},
    ).mappings().all()

    items = [
        BriefingItemResponse(
            id=str(row.get("id")),
            category=str(row.get("normalized_category") or row.get("keyword") or "기타"),
            title=str(row.get("title") or "제목 없음"),
            summary=(str(row.get("content") or "").strip()[:280] or str(row.get("title") or "제목 없음")),
            highlights=_build_highlights(str(row.get("content") or row.get("title") or "")),
            image_url=_thumbnail_from_url(
                (str(row.get("url")).strip() if row.get("url") else None),
                seed=str(row.get("id") or row.get("title") or "bookmark"),
            ),
            source_name=str(row.get("source_type") or "News Source"),
            published_at=(
                row.get("pub_date")
                if isinstance(row.get("pub_date"), datetime)
                else datetime.now(timezone.utc)
            ),
            read_time_minutes=_estimate_read_time(
                (str(row.get("content") or "").strip()[:280] or str(row.get("title") or ""))
            ),
            original_url=row.get("url"),
            is_bookmarked=True,
            feedback_type=(str(row.get("feedback_type")) if row.get("feedback_type") else None),
        )
        for row in rows
    ]
    return BriefingBookmarksResponse(items=items)
