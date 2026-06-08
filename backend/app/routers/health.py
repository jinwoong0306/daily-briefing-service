from fastapi import APIRouter

from app.db import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def db_health_check() -> dict[str, str]:
    return {"status": "ok" if check_db_connection() else "error"}
