from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.dependencies import get_current_user
from app.models import User, UserKeyword
from app.schemas import KeywordsResponse, KeywordsUpdateRequest

router = APIRouter(prefix="/users", tags=["keywords"])
settings = get_settings()


@router.get("/keywords", response_model=KeywordsResponse)
def get_my_keywords(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KeywordsResponse:
    keywords = db.scalars(
        select(UserKeyword.keyword)
        .where(UserKeyword.user_id == current_user.id)
        .order_by(UserKeyword.created_at.asc())
    ).all()
    return KeywordsResponse(user_id=current_user.id, keywords=keywords)


@router.put("/keywords", response_model=KeywordsResponse)
def update_my_keywords(
    payload: KeywordsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KeywordsResponse:
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

    return KeywordsResponse(user_id=current_user.id, keywords=payload.keywords)
