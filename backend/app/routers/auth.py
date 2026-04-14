import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import FixedWindowRateLimiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("uvicorn.error")
settings = get_settings()
login_rate_limiter = FixedWindowRateLimiter(
    max_attempts=settings.login_rate_limit_per_minute,
    period_seconds=60,
)


def _issue_token_response(email: str, password: str, db: Session) -> TokenResponse:
    normalized_email = email.lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(str(user.id))
    logger.info("Issued access token for user_id=%s via login", user.id)
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        ),
    )


def _rate_limit_key(email: str, request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}:{email.strip().lower()}"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized_email = payload.email.lower()
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    user = User(
        email=normalized_email,
        name=payload.name.strip() if payload.name else None,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    logger.info("Issued access token for user_id=%s via register", user.id)
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    limit_key = _rate_limit_key(payload.email, request)
    if not login_rate_limiter.allow(limit_key):
        logger.warning("Rate limit blocked login attempt key=%s", limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in a minute.",
        )
    token_response = _issue_token_response(payload.email, payload.password, db)
    login_rate_limiter.reset(limit_key)
    return token_response


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_with_oauth_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    # Swagger Authorize(OAuth2 password flow) submits username/password form fields.
    limit_key = _rate_limit_key(form_data.username, request)
    if not login_rate_limiter.allow(limit_key):
        logger.warning("Rate limit blocked oauth login attempt key=%s", limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in a minute.",
        )
    token_response = _issue_token_response(form_data.username, form_data.password, db)
    login_rate_limiter.reset(limit_key)
    return token_response
