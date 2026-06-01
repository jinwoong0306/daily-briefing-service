import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

TEST_DB_PATH = Path(__file__).parent / "test_api.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["INGEST_SCHEDULER_ENABLED"] = "false"
os.environ["INGEST_ADMIN_EMAILS"] = ""
os.environ["REDIS_URL"] = ""
os.environ["SUPABASE_URL"] = "https://example-project.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test-supabase-anon-key"

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.auth import login_rate_limiter  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402
from app.routers import ingest as ingest_router  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    if TEST_DB_PATH.exists():
        engine.dispose()
        TEST_DB_PATH.unlink()
    yield
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(autouse=True)
def reset_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    keyword TEXT,
                    source_type TEXT,
                    pub_date TEXT,
                    url TEXT
                )
                """
            )
        )
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def register_user(client: TestClient, email: str = "user1@example.com", password: str = "password123"):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "User One"},
    )


def login_user(client: TestClient, email: str = "user1@example.com", password: str = "password123"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def insert_article(
    *,
    article_id: int,
    title: str,
    keyword: str,
    content: str = "뉴스 본문",
    source_type: str = "Test Source",
    pub_date: str = "2026-05-08T03:00:00+00:00",
    url: str = "https://example.com/news",
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO articles (id, title, content, keyword, source_type, pub_date, url)
                VALUES (:id, :title, :content, :keyword, :source_type, :pub_date, :url)
                """
            ),
            {
                "id": article_id,
                "title": title,
                "content": content,
                "keyword": keyword,
                "source_type": source_type,
                "pub_date": pub_date,
                "url": url,
            },
        )


def test_auth_register_login_and_error_format(client: TestClient):
    register_response = register_user(client)
    assert register_response.status_code == 201
    register_body = register_response.json()
    assert register_body["token_type"] == "bearer"
    assert register_body["user"]["email"] == "user1@example.com"
    assert register_body["access_token"]

    duplicate_response = register_user(client)
    assert duplicate_response.status_code == 409
    duplicate_body = duplicate_response.json()
    assert duplicate_body["success"] is False
    assert duplicate_body["error"]["code"] == "CONFLICT"
    assert duplicate_body["error"]["message"] == "Email already exists"

    invalid_format_response = client.post(
        "/api/v1/auth/register",
        json={"email": "wrong-email-format", "password": "password123"},
    )
    assert invalid_format_response.status_code == 422
    invalid_format_body = invalid_format_response.json()
    assert invalid_format_body["success"] is False
    assert invalid_format_body["error"]["code"] == "VALIDATION_ERROR"
    assert len(invalid_format_body["error"]["details"]) > 0

    login_response = login_user(client)
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["token_type"] == "bearer"
    assert login_body["access_token"]

    oauth_login_response = client.post(
        "/api/v1/auth/token",
        data={"username": "user1@example.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert oauth_login_response.status_code == 200
    oauth_login_body = oauth_login_response.json()
    assert oauth_login_body["token_type"] == "bearer"
    assert oauth_login_body["access_token"]

    login_fail_response = login_user(client, password="wrong-password")
    assert login_fail_response.status_code == 401
    login_fail_body = login_fail_response.json()
    assert login_fail_body["success"] is False
    assert login_fail_body["error"]["code"] == "UNAUTHORIZED"
    assert login_fail_body["error"]["message"] == "Invalid email or password"


def test_login_rate_limit_blocks_bruteforce(client: TestClient):
    register_user(client, email="rate-limit@example.com")

    original_limit = login_rate_limiter.max_attempts
    login_rate_limiter.max_attempts = 2
    try:
        for _ in range(2):
            fail_response = login_user(client, email="rate-limit@example.com", password="wrong-password")
            assert fail_response.status_code == 401

        blocked_response = login_user(client, email="rate-limit@example.com", password="wrong-password")
        assert blocked_response.status_code == 429
        blocked_body = blocked_response.json()
        assert blocked_body["success"] is False
        assert blocked_body["error"]["code"] == "TOO_MANY_REQUESTS"
    finally:
        login_rate_limiter.max_attempts = original_limit
        login_rate_limiter.reset("testclient:rate-limit@example.com")


def test_google_login_via_supabase_exchange_returns_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    def _fake_fetch(_: str) -> dict:
        return {
            "email": "google-user@example.com",
            "app_metadata": {"provider": "google"},
            "user_metadata": {"name": "Google User"},
        }

    monkeypatch.setattr(auth_router, "_fetch_supabase_user", _fake_fetch)

    response = client.post(
        "/api/v1/auth/google/supabase",
        json={"access_token": "fake-supabase-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "google-user@example.com"

    # same account should login to existing user
    second = client.post(
        "/api/v1/auth/google/supabase",
        json={"access_token": "fake-supabase-token"},
    )
    assert second.status_code == 200
    assert second.json()["user"]["email"] == "google-user@example.com"


def test_get_my_profile_requires_auth_and_returns_user(client: TestClient):
    unauthorized_response = client.get("/api/v1/users/profile")
    assert unauthorized_response.status_code == 401
    unauthorized_body = unauthorized_response.json()
    assert unauthorized_body["success"] is False
    assert unauthorized_body["error"]["code"] == "UNAUTHORIZED"

    register_response = register_user(client, email="profile@example.com")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_response = client.get("/api/v1/users/profile", headers=headers)
    assert profile_response.status_code == 200
    profile_body = profile_response.json()
    assert profile_body["email"] == "profile@example.com"
    assert profile_body["id"] > 0
    assert "created_at" in profile_body


def test_keywords_settings_scope_validation(client: TestClient):
    unauthorized_response = client.get("/api/v1/users/keywords")
    assert unauthorized_response.status_code == 401
    unauthorized_body = unauthorized_response.json()
    assert unauthorized_body["success"] is False
    assert unauthorized_body["error"]["code"] == "UNAUTHORIZED"

    register_response = register_user(client)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_response = client.put(
        "/api/v1/users/keywords",
        headers=headers,
        json={"keywords": ["AI", "  ai", "Tech", ""]},
    )
    assert update_response.status_code == 200
    update_body = update_response.json()
    assert update_body["keywords"] == ["AI", "Tech"]

    get_response = client.get("/api/v1/users/keywords", headers=headers)
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["keywords"] == ["AI", "Tech"]
    assert get_body["version"]

    conflict_response = client.put(
        "/api/v1/users/keywords",
        headers=headers,
        json={"keywords": ["Science"], "expected_version": "stale-version"},
    )
    assert conflict_response.status_code == 409
    conflict_body = conflict_response.json()
    assert conflict_body["success"] is False
    assert conflict_body["error"]["code"] == "CONFLICT"


def test_notification_settings_get_and_update(client: TestClient):
    register_response = register_user(client)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    get_response = client.get("/api/v1/users/notifications", headers=headers)
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["enabled"] is True
    assert get_body["delivery_hour"] == 8
    assert get_body["delivery_minute"] == 0
    assert get_body["timezone"] == "Asia/Seoul"
    assert get_body["version"]

    update_response = client.put(
        "/api/v1/users/notifications",
        headers=headers,
        json={"enabled": False, "delivery_hour": 7, "delivery_minute": 30, "timezone": "UTC"},
    )
    assert update_response.status_code == 200
    update_body = update_response.json()
    assert update_body["enabled"] is False
    assert update_body["delivery_hour"] == 7
    assert update_body["delivery_minute"] == 30
    assert update_body["timezone"] == "UTC"
    assert update_body["version"]

    conflict_response = client.put(
        "/api/v1/users/notifications",
        headers=headers,
        json={
            "enabled": True,
            "delivery_hour": 9,
            "delivery_minute": 0,
            "timezone": "Asia/Seoul",
            "expected_version": "2000-01-01T00:00:00+00:00",
        },
    )
    assert conflict_response.status_code == 409
    conflict_body = conflict_response.json()
    assert conflict_body["success"] is False
    assert conflict_body["error"]["code"] == "CONFLICT"

    empty_payload_response = client.put("/api/v1/users/notifications", headers=headers, json={})
    assert empty_payload_response.status_code == 422
    empty_payload_body = empty_payload_response.json()
    assert empty_payload_body["success"] is False
    assert empty_payload_body["error"]["code"] == "VALIDATION_ERROR"

    invalid_hour_response = client.put(
        "/api/v1/users/notifications",
        headers=headers,
        json={"delivery_hour": 15, "delivery_minute": 0, "timezone": "Asia/Seoul"},
    )
    assert invalid_hour_response.status_code == 422


def test_briefing_actions_return_404_for_missing_article(client: TestClient):
    register_response = register_user(client, email="briefing-action@example.com")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    feedback_response = client.post(
        "/api/v1/briefings/99999/feedback",
        headers=headers,
        json={"feedback_type": "like"},
    )
    assert feedback_response.status_code == 404
    feedback_body = feedback_response.json()
    assert feedback_body["success"] is False
    assert feedback_body["error"]["code"] == "NOT_FOUND"

    bookmark_put_response = client.put(
        "/api/v1/briefings/99999/bookmark",
        headers=headers,
    )
    assert bookmark_put_response.status_code == 404
    bookmark_put_body = bookmark_put_response.json()
    assert bookmark_put_body["success"] is False
    assert bookmark_put_body["error"]["code"] == "NOT_FOUND"

    bookmark_delete_response = client.delete(
        "/api/v1/briefings/99999/bookmark",
        headers=headers,
    )
    assert bookmark_delete_response.status_code == 404
    bookmark_delete_body = bookmark_delete_response.json()
    assert bookmark_delete_body["success"] is False
    assert bookmark_delete_body["error"]["code"] == "NOT_FOUND"


def test_briefings_today_applies_category_normalization(client: TestClient):
    register_response = register_user(client, email="briefing-today@example.com")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    keywords_response = client.put(
        "/api/v1/users/keywords",
        headers=headers,
        json={"keywords": ["스포츠", "엔터테인먼트", "정치"]},
    )
    assert keywords_response.status_code == 200

    recent = datetime.now(timezone.utc).isoformat()
    insert_article(article_id=101, title="Sports headline", keyword="sports", pub_date=recent)
    insert_article(article_id=102, title="Politics headline", keyword="politics", pub_date=recent)
    insert_article(article_id=103, title="IT headline", keyword="IT/과학", pub_date=recent)

    response = client.get("/api/v1/briefings/today", headers=headers)
    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    categories = {item["category"] for item in body["items"]}

    assert "101" in ids
    assert "102" in ids
    assert "103" not in ids
    assert "스포츠" in categories
    assert "정치" in categories


def test_briefing_bookmark_flow_returns_saved_items(client: TestClient):
    register_response = register_user(client, email="briefing-bookmark@example.com")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    insert_article(article_id=201, title="Entertainment headline", keyword="entertainment")

    save_response = client.put("/api/v1/briefings/201/bookmark", headers=headers)
    assert save_response.status_code == 200

    bookmarks_response = client.get("/api/v1/briefings/bookmarks", headers=headers)
    assert bookmarks_response.status_code == 200
    bookmarks_body = bookmarks_response.json()

    assert len(bookmarks_body["items"]) == 1
    item = bookmarks_body["items"][0]
    assert item["id"] == "201"
    assert item["category"] == "엔터테인먼트"
    assert item["is_bookmarked"] is True


class _FakeRedis:
    def __init__(self):
        self._keys = {
            "news:list": "list",
            "news:stream": "stream",
            "briefing:2026-05-09:keyword:%EC%8A%A4%ED%8F%AC%EC%B8%A0": "string",
            "briefing:2026-05-09:user:1": "string",
        }

    def scan_iter(self, match="*", count=200):  # noqa: ANN001
        if match in ("", "*"):
            return iter(self._keys.keys())
        prefix = match.rstrip("*")
        return iter([key for key in self._keys if key.startswith(prefix)])

    def type(self, key: str) -> str:
        return self._keys.get(key, "none")

    def lrange(self, key: str, start: int, end: int):  # noqa: ARG002
        if key != "news:list":
            return []
        return [
            '{"title":"Redis News","content":"본문","keyword":"sports","source":"Redis","url":"https://example.com/redis-news","pub_date":"2026-05-09T00:00:00+00:00"}'
        ]

    def xrevrange(self, key: str, count: int):  # noqa: ARG002
        if key != "news:stream":
            return []
        return [("1-0", {"title": "Stream News", "keyword": "politics"})]

    def smembers(self, key: str):  # noqa: ARG002
        return set()

    def zrevrange(self, key: str, start: int, end: int, withscores: bool):  # noqa: ARG002
        return []

    def get(self, key: str):  # noqa: ARG002
        if key == "briefing:2026-05-09:keyword:%EC%8A%A4%ED%8F%AC%EC%B8%A0":
            return (
                '{"keyword":"���","items":[{"title":"Batch Redis News","summary":"요약",'
                '"url":"https://example.com/batch-redis-news","source_type":"Redis Batch",'
                '"pub_date":"2026-05-09T09:00:00+09:00"}]}'
            )
        if key == "briefing:2026-05-09:keyword:%EC%8A%A4%ED%8F%AC%EC%B8%A0":
            return (
                '{"keyword":"���","items":[{"title":"Batch Redis News","summary":"요약",'
                '"url":"https://example.com/batch-redis-news","source_type":"Redis Batch",'
                '"pub_date":"2026-05-09T09:00:00+09:00"}]}'
            )
        if key.startswith("briefing:") and key.endswith(":user:1"):
            return (
                '{"briefing_date":"2026-05-09","user_id":"1","keywords":[{"keyword":"AI",'
                '"headline":"AI 헤드라인","summary":"AI 요약","items":[{"id":"123","title":"AI 기사",'
                '"summary":"기사 요약","url":"https://example.com/ai","source_type":"naver",'
                '"pub_date":"2026-05-09T01:00:00+09:00"}]}]}'
            )
        return None


def test_ingest_redis_keys_and_pull(client: TestClient):
    register_response = register_user(client, email="ingest@example.com")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    original_client_factory = ingest_router._redis_client
    ingest_router._redis_client = lambda: _FakeRedis()
    try:
        keys_response = client.get("/api/v1/ingest/redis/keys", headers=headers)
        assert keys_response.status_code == 200
        keys_body = keys_response.json()
        assert keys_body["total_keys"] >= 2

        pull_response = client.post(
            "/api/v1/ingest/redis/pull?key=news:list&limit=10",
            headers=headers,
        )
        assert pull_response.status_code == 200
        pull_body = pull_response.json()
        assert pull_body["fetched"] == 1
        assert pull_body["created"] == 1

        briefings_response = client.get("/api/v1/briefings/today", headers=headers)
        assert briefings_response.status_code == 200
        items = briefings_response.json()["items"]
        assert any(item["title"] == "Redis News" for item in items)
    finally:
        ingest_router._redis_client = original_client_factory


def test_ingest_redis_batch_pull(client: TestClient):
    register_response = register_user(client, email="ingest-batch@example.com")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    original_client_factory = ingest_router._redis_client
    ingest_router._redis_client = lambda: _FakeRedis()
    try:
        batch_response = client.post(
            "/api/v1/ingest/redis/pull/batch?match=briefing:*&per_key_limit=10&max_keys=10",
            headers=headers,
        )
        assert batch_response.status_code == 200
        batch_body = batch_response.json()
        assert batch_body["keys_processed"] >= 1
        assert batch_body["fetched"] >= 1
        assert batch_body["created"] >= 1

        briefings_response = client.get("/api/v1/briefings/today", headers=headers)
        assert briefings_response.status_code == 200
        items = briefings_response.json()["items"]
        assert any(item["title"] == "Batch Redis News" for item in items)
        assert any(item["category"] == "스포츠" for item in items)
    finally:
        ingest_router._redis_client = original_client_factory


def test_briefings_today_grouped_reads_user_briefing_from_redis(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    register_response = register_user(client, email="grouped-briefing@example.com")
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setattr("app.routers.briefings.settings.redis_url", "redis://fake")
    monkeypatch.setattr("app.routers.briefings._redis_client", lambda: _FakeRedis())
    response = client.get("/api/v1/briefings/today/grouped", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "1"
    assert len(body["keywords"]) == 1
    assert body["keywords"][0]["keyword"] == "AI"
    assert body["keywords"][0]["items"][0]["title"] == "AI 기사"


def test_briefings_today_grouped_filtered_to_saved_keywords(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
):
    from app.routers import briefings as briefings_router
    from app.schemas import (
        BriefingGroupedKeywordItemResponse,
        BriefingGroupedKeywordResponse,
        BriefingsTodayGroupedResponse,
    )

    register_response = register_user(client, email="grouped-filter@example.com")
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]
    user_id = register_response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    put_resp = client.put(
        "/api/v1/users/keywords",
        headers=headers,
        json={"keywords": ["정치", "IT/과학"]},
    )
    assert put_resp.status_code == 200

    stale = BriefingsTodayGroupedResponse(
        briefing_date="2026-05-19",
        user_id=str(user_id),
        keywords=[
            BriefingGroupedKeywordResponse(
                keyword="정치",
                headline="H1",
                summary="S1",
                items=[
                    BriefingGroupedKeywordItemResponse(
                        id="1",
                        title="Politics News",
                        summary="Sum",
                        url="https://example.com/p",
                        source_type="t",
                    )
                ],
            ),
            BriefingGroupedKeywordResponse(
                keyword="스포츠",
                headline="H2",
                summary="S2",
                items=[
                    BriefingGroupedKeywordItemResponse(
                        id="2",
                        title="Sports News",
                        summary="Sum",
                        url="https://example.com/s",
                        source_type="t",
                    )
                ],
            ),
        ],
    )

    monkeypatch.setattr(
        briefings_router,
        "_load_redis_user_grouped",
        lambda current_user: stale,
    )
    response = client.get("/api/v1/briefings/today/grouped", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["keywords"]) == 1
    assert body["keywords"][0]["keyword"] == "정치"
    assert body["keywords"][0]["items"][0]["title"] == "Politics News"


def test_briefings_today_grouped_falls_back_to_db_sections(client: TestClient):
    """Redis 묶음 없을 때 today 기사를 카테고리 섹션으로 돌려준다."""
    register_response = register_user(client, email="grouped-db-fallback@example.com")
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    recent = datetime.now(timezone.utc).isoformat()

    put_resp = client.put(
        "/api/v1/users/keywords",
        headers=headers,
        json={"keywords": ["경제", "정치"]},
    )
    assert put_resp.status_code == 200

    insert_article(article_id=301, title="Economy A", keyword="economy", pub_date=recent)
    insert_article(article_id=302, title="Politics A", keyword="politics", pub_date=recent)

    response = client.get("/api/v1/briefings/today/grouped", headers=headers)
    assert response.status_code == 200
    body = response.json()
    kws = {b["keyword"] for b in body["keywords"]}
    assert "경제" in kws
    assert "정치" in kws
    assert any(b.get("headline") for b in body["keywords"])
    assert any(b.get("summary") for b in body["keywords"])


def test_ingest_admin_email_restriction(client: TestClient):
    blocked_register = register_user(client, email="blocked-ingest@example.com")
    blocked_token = blocked_register.json()["access_token"]
    blocked_headers = {"Authorization": f"Bearer {blocked_token}"}

    allowed_register = register_user(client, email="allowed-ingest@example.com")
    allowed_token = allowed_register.json()["access_token"]
    allowed_headers = {"Authorization": f"Bearer {allowed_token}"}

    original_admin_emails = ingest_router.settings.ingest_admin_emails
    original_client_factory = ingest_router._redis_client
    ingest_router.settings.ingest_admin_emails = "allowed-ingest@example.com"
    ingest_router._redis_client = lambda: _FakeRedis()
    try:
        blocked_response = client.get("/api/v1/ingest/redis/keys", headers=blocked_headers)
        assert blocked_response.status_code == 403
        blocked_body = blocked_response.json()
        assert blocked_body["success"] is False
        assert blocked_body["error"]["code"] == "FORBIDDEN"

        allowed_response = client.get("/api/v1/ingest/redis/keys", headers=allowed_headers)
        assert allowed_response.status_code == 200
    finally:
        ingest_router.settings.ingest_admin_emails = original_admin_emails
        ingest_router._redis_client = original_client_factory
