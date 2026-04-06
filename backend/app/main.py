from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.db import Base, check_db_connection, engine
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.keywords import router as keywords_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # BE-002: 환경별 설정으로 테이블 자동 생성을 제어
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    if not check_db_connection():
        logger.warning("Database connectivity check failed during startup.")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(keywords_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name}
