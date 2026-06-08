from datetime import datetime, timezone
import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import TTLCache
from app.core.config import get_settings
from app.core.metrics import SlidingWindowMetrics
from app.db import get_db
from app.dependencies import get_current_user
from app.models import User, UserNotificationSetting
from app.schemas import NotificationSettingsResponse, NotificationSettingsUpdateRequest

router = APIRouter(prefix="/users", tags=["notifications"])
settings = get_settings()
logger = logging.getLogger("uvicorn.error")
notifications_cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)
settings_update_metrics = SlidingWindowMetrics(maxlen=settings.api_settings_metrics_window_size)


def _cache_key(user_id: int) -> str:
    return f"notifications:{user_id}"


def _version(updated_at: datetime) -> str:
    return updated_at.isoformat()


def _normalize_version(value: str) -> str:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return value


def _get_or_create_user_notification_settings(user_id: int, db: Session) -> UserNotificationSetting:
    notification_settings = db.scalar(
        select(UserNotificationSetting).where(UserNotificationSetting.user_id == user_id)
    )
    if notification_settings is not None:
        return notification_settings

    notification_settings = UserNotificationSetting(user_id=user_id)
    db.add(notification_settings)
    db.commit()
    db.refresh(notification_settings)
    return notification_settings


def _to_response(user_id: int, notification_settings: UserNotificationSetting) -> NotificationSettingsResponse:
    return NotificationSettingsResponse(
        user_id=user_id,
        enabled=notification_settings.enabled,
        delivery_hour=notification_settings.delivery_hour,
        delivery_minute=notification_settings.delivery_minute,
        timezone=notification_settings.timezone_name,
        updated_at=notification_settings.updated_at,
        version=_version(notification_settings.updated_at),
    )


@router.get("/notifications", response_model=NotificationSettingsResponse)
def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationSettingsResponse:
    cache_key = _cache_key(current_user.id)
    cached = notifications_cache.get(cache_key)
    if cached is not None:
        logger.warning(
            "Settings cache hit (notifications) user_id=%s ttl_seconds=%s",
            current_user.id,
            settings.cache_ttl_seconds,
        )
        return cached
    logger.warning(
        "Settings cache miss (notifications) user_id=%s ttl_seconds=%s",
        current_user.id,
        settings.cache_ttl_seconds,
    )

    notification_settings = _get_or_create_user_notification_settings(current_user.id, db)
    response = _to_response(current_user.id, notification_settings)
    notifications_cache.set(cache_key, response)
    return response


@router.put("/notifications", response_model=NotificationSettingsResponse)
def update_notification_settings(
    payload: NotificationSettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationSettingsResponse:
    started_at = perf_counter()
    if not payload.has_any_field:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one notification setting field is required",
        )

    notification_settings = _get_or_create_user_notification_settings(current_user.id, db)
    current_version = _normalize_version(_version(notification_settings.updated_at))
    expected_version = (
        _normalize_version(payload.expected_version) if payload.expected_version is not None else None
    )
    if expected_version is not None and expected_version != current_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Notification settings were updated by another request. Refresh and retry.",
        )

    if payload.enabled is not None:
        notification_settings.enabled = payload.enabled
    if payload.delivery_hour is not None:
        notification_settings.delivery_hour = payload.delivery_hour
    if payload.delivery_minute is not None:
        notification_settings.delivery_minute = payload.delivery_minute
    if payload.timezone is not None:
        notification_settings.timezone_name = payload.timezone

    notification_settings.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification_settings)
    notifications_cache.delete(_cache_key(current_user.id))
    logger.warning("Settings cache invalidated (notifications) user_id=%s", current_user.id)

    elapsed_ms = (perf_counter() - started_at) * 1000
    avg_ms, p95_ms = settings_update_metrics.add(elapsed_ms)
    logger.warning(
        "Settings update metrics (notifications) elapsed_ms=%.2f avg_ms=%.2f p95_ms=%.2f",
        elapsed_ms,
        avg_ms,
        p95_ms,
    )

    return _to_response(current_user.id, notification_settings)
