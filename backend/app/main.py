from contextlib import asynccontextmanager
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.core.config import get_settings
from app.db import Base, check_db_connection, engine
from app.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.routers.auth import router as auth_router
from app.routers.briefings import router as briefings_router
from app.routers.health import router as health_router
from app.routers.ingest import router as ingest_router
from app.routers.ingest import run_redis_ingest_batch
from app.routers.keywords import router as keywords_router
from app.routers.notifications import router as notifications_router
from app.routers.profile import router as profile_router

settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
scheduler: BackgroundScheduler | None = None


def _scheduled_redis_ingest_batch() -> None:
    try:
        run_redis_ingest_batch(
            match=settings.ingest_batch_match,
            per_key_limit=settings.ingest_batch_per_key_limit,
            max_keys=settings.ingest_batch_max_keys,
        )
    except Exception as exc:
        logger.warning("Scheduled Redis ingest failed: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global scheduler
    # BE-002: 환경별 설정으로 테이블 자동 생성을 제어
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    if settings.jwt_secret_key == "change-this-secret-in-production":
        logger.warning(
            "JWT_SECRET_KEY is still set to the default value. "
            "Set a strong secret before production deployment."
        )

    if not check_db_connection():
        logger.warning("Database connectivity check failed during startup.")
    if settings.ingest_scheduler_enabled:
        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            _scheduled_redis_ingest_batch,
            trigger="interval",
            minutes=settings.ingest_scheduler_interval_minutes,
            id="redis_ingest_batch",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            "Started Redis ingest scheduler interval_minutes=%s match=%s per_key_limit=%s max_keys=%s",
            settings.ingest_scheduler_interval_minutes,
            settings.ingest_batch_match,
            settings.ingest_batch_per_key_limit,
            settings.ingest_batch_max_keys,
        )
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            logger.info("Stopped Redis ingest scheduler")
            scheduler = None


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(briefings_router, prefix=settings.api_prefix)
app.include_router(ingest_router, prefix=settings.api_prefix)
app.include_router(keywords_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)
app.include_router(profile_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name}
