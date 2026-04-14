import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB_PATH = Path(__file__).parent / "test_api.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.auth import login_rate_limiter  # noqa: E402


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
