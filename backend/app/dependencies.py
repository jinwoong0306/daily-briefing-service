import logging
from time import perf_counter

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.metrics import SlidingWindowMetrics
from app.core.security import decode_access_token
from app.db import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
logger = logging.getLogger("uvicorn.error")
settings = get_settings()
auth_validation_metrics = SlidingWindowMetrics(maxlen=settings.auth_metrics_window_size)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    started_at = perf_counter()
    try:
        payload = decode_access_token(token)
    except ValueError:
        logger.warning("Access token validation failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from None

    subject = payload.get("sub")
    if not subject:
        logger.warning("Access token payload missing subject")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token payload",
        )

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        logger.warning("Access token subject is not a valid user id")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token payload",
        ) from None

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        logger.warning("Access token subject user not found: user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    elapsed_ms = (perf_counter() - started_at) * 1000
    avg_ms, p95_ms = auth_validation_metrics.add(elapsed_ms)
    logger.warning(
        "Validated access token for user_id=%s (elapsed_ms=%.2f, avg_ms=%.2f, p95_ms=%.2f)",
        user_id,
        elapsed_ms,
        avg_ms,
        p95_ms,
    )
    if elapsed_ms > 50:
        logger.warning("Token validation exceeded 50ms threshold: %.2fms", elapsed_ms)
    return user
