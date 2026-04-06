from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


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
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized_email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        ),
    )
