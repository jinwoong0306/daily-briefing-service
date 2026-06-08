from datetime import datetime, timezone
import json
import logging
from time import perf_counter
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import SessionLocal, get_db
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/ingest", tags=["ingest"])
settings = get_settings()
logger = logging.getLogger("uvicorn.error")


def _ingest_admin_email_set() -> set[str]:
    if not settings.ingest_admin_emails:
        return set()
    return {
        email.strip().lower()
        for email in settings.ingest_admin_emails.split(",")
        if email.strip()
    }


def _assert_ingest_admin(current_user: User) -> None:
    allowed_emails = _ingest_admin_email_set()
    if not allowed_emails:
        return
    if current_user.email.lower() not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to trigger ingest endpoints",
        )


def _table_name(name: str, db: Session) -> str:
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        return name
    return f"public.{name}"


def _redis_client() -> Redis:
    if not settings.redis_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="REDIS_URL is not configured",
        )
    redis_url = settings.redis_url.strip()
    # Upstash commonly requires TLS; users often share redis:// URLs.
    if redis_url.startswith("redis://") and ".upstash.io" in redis_url:
        redis_url = "rediss://" + redis_url[len("redis://") :]
    return Redis.from_url(redis_url, decode_responses=True)


def _decode_payload(payload: Any) -> Any:
    if isinstance(payload, (dict, list)):
        return payload
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
    return None


def _pick(data: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        text_value = str(value).strip()
        if text_value:
            return text_value
    return None


def _normalize_pub_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _normalize_news_item(data: dict[str, Any]) -> dict[str, Any] | None:
    title = _pick(data, ["title", "headline", "news_title"])
    url = _pick(data, ["url", "link", "original_url", "origin_url"])
    if not title:
        return None
    if not url:
        return None

    return {
        "title": title,
        "content": _pick(data, ["content", "summary", "description", "body"]) or title,
        "keyword": _pick(data, ["keyword", "category", "topic"]) or "기타",
        "source_type": _pick(data, ["source_type", "source", "publisher"]) or "Redis Feed",
        "pub_date": _normalize_pub_date(
            _pick(data, ["pub_date", "published_at", "publishedAt", "created_at"])
        ),
        "url": url,
    }


def _looks_broken_text(value: str | None) -> bool:
    if not value:
        return True
    # Common mojibake marker when UTF-8 bytes are decoded incorrectly.
    return "�" in value


def _infer_keyword_from_key(key: str) -> str | None:
    marker = ":keyword:"
    if marker not in key:
        return None
    encoded = key.split(marker, 1)[1]
    decoded = unquote(encoded).strip()
    return decoded or None


def _upsert_article(item: dict[str, Any], db: Session) -> str:
    articles_table = _table_name("articles", db)
    existing_id = None
    if item["url"]:
        existing_id = db.execute(
            text(f"select id from {articles_table} where url = :url limit 1"),
            {"url": item["url"]},
        ).scalar()

    if existing_id is not None:
        db.execute(
            text(
                f"""
                update {articles_table}
                set title = :title,
                    content = :content,
                    keyword = :keyword,
                    source_type = :source_type,
                    pub_date = :pub_date
                where id = :id
                """
            ),
            {
                "id": existing_id,
                "title": item["title"],
                "content": item["content"],
                "keyword": item["keyword"],
                "source_type": item["source_type"],
                "pub_date": item["pub_date"],
            },
        )
        return "updated"

    db.execute(
        text(
            f"""
            insert into {articles_table}
            (title, content, keyword, source_type, pub_date, url)
            values (:title, :content, :keyword, :source_type, :pub_date, :url)
            """
        ),
        item,
    )
    return "created"


def _read_from_key(client: Redis, key: str, limit: int) -> list[dict[str, Any]]:
    key_type = client.type(key)
    payloads: list[Any] = []

    if key_type == "stream":
        payloads = [entry[1] for entry in client.xrevrange(key, count=limit)]
    elif key_type == "list":
        payloads = client.lrange(key, 0, limit - 1)
    elif key_type == "set":
        payloads = list(client.smembers(key))[:limit]
    elif key_type == "zset":
        payloads = [value for value, _ in client.zrevrange(key, 0, limit - 1, withscores=True)]
    elif key_type == "string":
        value = client.get(key)
        payloads = [value] if value else []
    else:
        return []

    records: list[dict[str, Any]] = []
    for raw in payloads:
        decoded = _decode_payload(raw)
        records.extend(_extract_records(decoded))
        if len(records) >= limit:
            break
    return records[:limit]


def _extract_records(decoded: Any) -> list[dict[str, Any]]:
    if decoded is None:
        return []
    if isinstance(decoded, dict):
        container_fields = ["items", "articles", "selected_articles", "news", "results"]
        parent_keyword = _pick(decoded, ["keyword", "category", "topic"])
        for field in container_fields:
            value = decoded.get(field)
            if isinstance(value, list):
                items: list[dict[str, Any]] = []
                for entry in value:
                    if isinstance(entry, dict):
                        if parent_keyword and not _pick(entry, ["keyword", "category", "topic"]):
                            items.append({**entry, "keyword": parent_keyword})
                        else:
                            items.append(entry)
                if items:
                    return items
        nested_payload = decoded.get("payload") or decoded.get("data") or decoded.get("message")
        nested_decoded = _decode_payload(nested_payload)
        if nested_decoded is not None:
            nested_items = _extract_records(nested_decoded)
            if nested_items:
                return nested_items
        return [decoded]
    if isinstance(decoded, list):
        return [item for item in decoded if isinstance(item, dict)]
    return []


def _ingest_records_for_key(
    *,
    db: Session,
    key: str,
    raw_items: list[dict[str, Any]],
) -> dict[str, int | str]:
    inferred_keyword = _infer_keyword_from_key(key)
    created = 0
    updated = 0
    skipped = 0
    for raw in raw_items:
        prepared = dict(raw)
        existing_keyword = _pick(prepared, ["keyword", "category", "topic"])
        if inferred_keyword and _looks_broken_text(existing_keyword):
            prepared["keyword"] = inferred_keyword

        item = _normalize_news_item(prepared)
        if item is None:
            skipped += 1
            continue
        try:
            status_text = _upsert_article(item, db)
        except SQLAlchemyError:
            db.rollback()
            skipped += 1
            continue
        if status_text == "created":
            created += 1
        else:
            updated += 1
    db.commit()
    return {
        "key": key,
        "fetched": len(raw_items),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


def _run_batch_ingest(
    *,
    client: Redis,
    db: Session,
    match: str,
    per_key_limit: int,
    max_keys: int,
) -> dict[str, Any]:
    keys = list(client.scan_iter(match=match, count=settings.redis_scan_count))[:max_keys]

    per_key_results: list[dict[str, Any]] = []
    total_fetched = 0
    total_created = 0
    total_updated = 0
    total_skipped = 0

    for key in keys:
        try:
            raw_items = _read_from_key(client, key=key, limit=per_key_limit)
        except RedisError:
            per_key_results.append(
                {
                    "key": key,
                    "fetched": 0,
                    "created": 0,
                    "updated": 0,
                    "skipped": 0,
                    "error": "redis_read_failed",
                }
            )
            continue
        result = _ingest_records_for_key(db=db, key=key, raw_items=raw_items)
        per_key_results.append(result)
        total_fetched += int(result["fetched"])
        total_created += int(result["created"])
        total_updated += int(result["updated"])
        total_skipped += int(result["skipped"])

    return {
        "match": match,
        "keys_processed": len(keys),
        "per_key_limit": per_key_limit,
        "max_keys": max_keys,
        "fetched": total_fetched,
        "created": total_created,
        "updated": total_updated,
        "skipped": total_skipped,
        "results": per_key_results,
    }


def run_redis_ingest_batch(
    *,
    match: str,
    per_key_limit: int,
    max_keys: int,
) -> dict[str, Any]:
    started_at = perf_counter()
    client = _redis_client()
    db = SessionLocal()
    try:
        result = _run_batch_ingest(
            client=client,
            db=db,
            match=match,
            per_key_limit=per_key_limit,
            max_keys=max_keys,
        )
    finally:
        db.close()
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "Redis ingest batch match=%s keys=%s fetched=%s created=%s updated=%s skipped=%s elapsed_ms=%.2f",
        result["match"],
        result["keys_processed"],
        result["fetched"],
        result["created"],
        result["updated"],
        result["skipped"],
        elapsed_ms,
    )
    return {**result, "elapsed_ms": round(elapsed_ms, 2)}


@router.get("/redis/keys")
def get_redis_keys(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    _assert_ingest_admin(current_user)
    try:
        client = _redis_client()
        keys = list(client.scan_iter(match="*", count=settings.redis_scan_count))
        summary = [{"key": key, "type": client.type(key)} for key in keys[:100]]
        return {"total_keys": len(keys), "keys": summary}
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read from Redis: {exc}",
        ) from exc


@router.post("/redis/pull")
def pull_news_from_redis(
    key: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _assert_ingest_admin(current_user)
    started_at = perf_counter()
    try:
        client = _redis_client()
        raw_items = _read_from_key(client, key=key, limit=limit)
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read from Redis: {exc}",
        ) from exc

    result = _ingest_records_for_key(db=db, key=key, raw_items=raw_items)
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "Redis ingest single key=%s fetched=%s created=%s updated=%s skipped=%s elapsed_ms=%.2f",
        result["key"],
        result["fetched"],
        result["created"],
        result["updated"],
        result["skipped"],
        elapsed_ms,
    )

    return {
        **result,
        "requested_limit": limit,
        "elapsed_ms": round(elapsed_ms, 2),
    }


@router.post("/redis/pull/batch")
def pull_news_from_redis_batch(
    match: str = Query("briefing:*", min_length=1),
    per_key_limit: int = Query(50, ge=1, le=500),
    max_keys: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _assert_ingest_admin(current_user)
    started_at = perf_counter()
    try:
        client = _redis_client()
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read from Redis: {exc}",
        ) from exc

    result = _run_batch_ingest(
        client=client,
        db=db,
        match=match,
        per_key_limit=per_key_limit,
        max_keys=max_keys,
    )

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "Redis ingest batch match=%s keys=%s fetched=%s created=%s updated=%s skipped=%s elapsed_ms=%.2f",
        result["match"],
        result["keys_processed"],
        result["fetched"],
        result["created"],
        result["updated"],
        result["skipped"],
        elapsed_ms,
    )

    return {
        **result,
        "elapsed_ms": round(elapsed_ms, 2),
    }
