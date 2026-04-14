import hashlib
import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.cache import TTLCache
from app.core.config import get_settings
from app.core.metrics import SlidingWindowMetrics
from app.db import get_db
from app.dependencies import get_current_user
from app.models import User, UserKeyword
from app.schemas import KeywordsResponse, KeywordsUpdateRequest

router = APIRouter(prefix="/users", tags=["keywords"])
settings = get_settings()
logger = logging.getLogger("uvicorn.error")
keywords_cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)
settings_update_metrics = SlidingWindowMetrics(maxlen=settings.api_settings_metrics_window_size)


def _keywords_cache_key(user_id: int) -> str:
    return f"keywords:{user_id}"


def _keywords_version(keywords: list[str]) -> str:
    raw = "|".join(keyword.lower() for keyword in keywords)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@router.get("/keywords", response_model=KeywordsResponse)
def get_my_keywords(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KeywordsResponse:
    cache_key = _keywords_cache_key(current_user.id)
    cached = keywords_cache.get(cache_key)
    if cached is not None:
        logger.warning(
            "Settings cache hit (keywords) user_id=%s ttl_seconds=%s",
            current_user.id,
            settings.cache_ttl_seconds,
        )
        return cached
    logger.warning(
        "Settings cache miss (keywords) user_id=%s ttl_seconds=%s",
        current_user.id,
        settings.cache_ttl_seconds,
    )

    keywords = db.scalars(
        select(UserKeyword.keyword)
        .where(UserKeyword.user_id == current_user.id)
        .order_by(UserKeyword.created_at.asc())
    ).all()
    response = KeywordsResponse(
        user_id=current_user.id,
        keywords=keywords,
        version=_keywords_version(keywords),
    )
    keywords_cache.set(cache_key, response)
    return response


@router.put("/keywords", response_model=KeywordsResponse)
def update_my_keywords(
    payload: KeywordsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KeywordsResponse:
    started_at = perf_counter()
    existing_keywords = db.scalars(
        select(UserKeyword.keyword)
        .where(UserKeyword.user_id == current_user.id)
        .order_by(UserKeyword.created_at.asc())
    ).all()
    current_version = _keywords_version(existing_keywords)
    if payload.expected_version is not None and payload.expected_version != current_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Keywords were updated by another request. Refresh and retry.",
        )

    keyword_count = len(payload.keywords)
    if keyword_count < settings.keyword_min_count or keyword_count > settings.keyword_max_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Keywords must be between {settings.keyword_min_count} "
                f"and {settings.keyword_max_count} items"
            ),
        )

    db.execute(delete(UserKeyword).where(UserKeyword.user_id == current_user.id))
    db.add_all(
        [UserKeyword(user_id=current_user.id, keyword=keyword) for keyword in payload.keywords]
    )
    db.commit()
    keywords_cache.delete(_keywords_cache_key(current_user.id))
    logger.warning("Settings cache invalidated (keywords) user_id=%s", current_user.id)

    elapsed_ms = (perf_counter() - started_at) * 1000
    avg_ms, p95_ms = settings_update_metrics.add(elapsed_ms)
    logger.warning(
        "Settings update metrics (keywords) elapsed_ms=%.2f avg_ms=%.2f p95_ms=%.2f",
        elapsed_ms,
        avg_ms,
        p95_ms,
    )

    return KeywordsResponse(
        user_id=current_user.id,
        keywords=payload.keywords,
        version=_keywords_version(payload.keywords),
    )
