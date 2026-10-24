"""Offline regression across the sibling pipeline and API repositories."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker


def test_pipeline_cache_reaches_authenticated_today_and_grouped(
    monkeypatch, tmp_path,
):
    backend = Path(__file__).resolve().parents[1]
    pipeline_dir = (
        backend.parents[1] / "daily-briefing-pipeline" / "backend" / "pipeline"
    )
    monkeypatch.syspath_prepend(str(backend))
    monkeypatch.syspath_prepend(str(pipeline_dir))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET_KEY", "pipeline-handoff-test-secret")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("INGEST_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("PIPELINE_COLLECTION_START_HOUR", "20")
    monkeypatch.setenv("PIPELINE_COLLECTION_END_HOUR", "6")
    monkeypatch.setenv("BRIEFING_CANDIDATE_LIMIT", "3")
    monkeypatch.setenv("BRIEFING_MIN_ITEMS_PER_KEYWORD", "1")
    monkeypatch.setenv("BRIEFING_MAX_ITEMS_PER_KEYWORD", "2")
    monkeypatch.setenv("BRIEFING_SELECTION_PREVIEW_CHARS", "600")
    monkeypatch.setenv("BRIEFING_SUMMARY_CONTENT_CHARS", "4000")
    monkeypatch.setenv("BRIEFING_REDIS_TTL_SECONDS", "172800")

    ai_briefing = import_module("ai_briefing")
    redis_cache = import_module("redis_cache")
    uploader = import_module("supabase_uploader")
    api_db = import_module("app.db")
    api_main = import_module("app.main")
    briefings = import_module("app.routers.briefings")
    security = import_module("app.core.security")
    models = import_module("app.models")

    instant = datetime(2026, 10, 21, 23, 0, tzinfo=timezone.utc)
    edition_for = briefings._briefing_date
    edition = edition_for(instant)
    assert edition == "2026-10-22"
    assert instant.date().isoformat() != edition

    class Morning(datetime):
        @classmethod
        def now(cls, tz=None):
            return (
                instant.astimezone(tz)
                if tz else instant.replace(tzinfo=None)
            )

    monkeypatch.setattr(ai_briefing, "datetime", Morning)
    monkeypatch.setattr(
        briefings, "_briefing_date", lambda: edition_for(instant),
    )
    monkeypatch.setattr(api_main.settings, "auto_create_tables", False)
    monkeypatch.setattr(api_main.settings, "ingest_scheduler_enabled", False)
    monkeypatch.setattr(api_main.settings, "redis_url", "")

    engine = create_engine(
        f"sqlite:///{(tmp_path / 'handoff.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(api_db, "engine", engine)
    monkeypatch.setattr(api_main, "engine", engine)
    api_db.Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE articles ("
            "id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT, "
            "keyword TEXT, source_type TEXT, pub_date TEXT, url TEXT)"
        ))

    def get_db():
        with sessions() as db:
            yield db

    monkeypatch.setitem(
        api_main.app.dependency_overrides, api_db.get_db, get_db,
    )
    user_id = 71
    keyword = "IT/\uacfc\ud559"
    with sessions() as db:
        db.add(models.User(
            id=user_id, email="handoff@example.test", password_hash="unused",
        ))
        db.commit()
    token = security.create_access_token(str(user_id))
    headers = {"Authorization": f"Bearer {token}"}

    articles = [
        {
            "id": f"https://example.test/article-{index}",
            "keyword": keyword,
            "title": f"Source article {index}",
            "url": f"https://example.test/article-{index}",
            "content": f"Original report {index}. " * 400,
            "pub_date": f"2026-10-22T0{index}:00:00+09:00",
            "source_type": "offline-source",
        }
        for index in range(1, 4)
    ]
    batch = {
        "status": "success",
        "briefing_date": edition,
        "candidate_source": "cluster_representatives",
        "articles": articles,
    }
    original = deepcopy(batch)
    selected = articles[:2]
    expected_ids = [
        str(int(hashlib.sha256(row["url"].encode()).hexdigest()[:8], 16))
        for row in selected
    ]
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles "
                "(id, title, content, keyword, source_type, pub_date, url) "
                "VALUES (:id, :title, :content, :keyword, :source_type, "
                ":pub_date, :url)"
            ),
            {**selected[0], "id": int(expected_ids[0])},
        )

    class MemoryRedis:
        def __init__(self):
            self.values = {}
            self.reads = []
            self.ttls = {}

        def setex(self, key, ttl, payload):
            self.values[key] = payload
            self.ttls[key] = ttl

        def get(self, key):
            self.reads.append(key)
            return self.values.get(key)

    cache = MemoryRedis()
    monkeypatch.setattr(redis_cache, "get_redis_client", lambda: cache)
    monkeypatch.setattr(briefings, "_redis_client", lambda: cache)
    no_raw_query = Mock(
        side_effect=AssertionError("Raw article lookup is forbidden"),
    )
    monkeypatch.setattr(
        ai_briefing, "fetch_recent_articles_for_keyword", no_raw_query,
    )
    monkeypatch.setattr(
        ai_briefing, "extract_thumbnail_url",
        Mock(return_value={
            "thumbnail_url": "https://example.test/thumbnail.png",
            "thumbnail_status": "found",
        }),
    )
    ai = Mock(model="offline-model", model_status="configured")
    ai.select_article_ids.return_value = [row["id"] for row in selected]
    ai.summarize_keyword.side_effect = lambda label, inputs: {
        "headline": "Selected edition headline",
        "summary": "Selected edition overview",
        "summary_status": "configured",
        "items": [
            {
                key: row[key]
                for key in (
                    "id", "title", "url", "thumbnail_url",
                    "pub_date", "source_type",
                )
            } | {"summary": f"AI summary for {row['title']}"}
            for row in inputs
        ],
    }
    monkeypatch.setattr(ai_briefing, "OpenAIBriefingAI", lambda: ai)

    try:
        with TestClient(api_main.app) as client:
            assert client.get("/api/v1/briefings/today").status_code == 401
            saved = client.put(
                "/api/v1/users/keywords", headers=headers,
                json={"keywords": [keyword]},
            )
            assert saved.status_code == 200
            with sessions() as db:
                subscriptions = [
                    {"user_id": str(uid), "keyword": label}
                    for uid, label in db.execute(select(
                        models.UserKeyword.user_id, models.UserKeyword.keyword,
                    )).all()
                ]
            assert subscriptions == [
                {"user_id": str(user_id), "keyword": keyword},
            ]
            supabase = Mock()
            query = supabase.table.return_value.select.return_value
            query.execute.return_value = SimpleNamespace(data=subscriptions)
            monkeypatch.setattr(
                uploader, "get_supabase_client", lambda: supabase,
            )

            result = ai_briefing.generate_and_cache_briefings(
                candidate_batch=batch,
            )

            assert result["briefing_date"] == edition
            assert result["redis_saved"] == 2
            supabase.table.assert_called_once_with("user_keywords")
            supabase.table.return_value.select.assert_called_once_with(
                "user_id, keyword",
            )
            keyword_key = redis_cache.build_keyword_briefing_key(
                edition, keyword,
            )
            user_key = redis_cache.build_user_briefing_key(
                edition, str(user_id),
            )
            assert set(cache.values) == {keyword_key, user_key}
            assert cache.ttls == {keyword_key: 172800, user_key: 172800}
            keyword_payload = json.loads(cache.values[keyword_key])
            user_payload = json.loads(cache.values[user_key])
            assert user_payload["briefing_date"] == edition
            assert user_payload["keywords"] == [keyword_payload]
            assert keyword_payload["generated_at"] == (
                "2026-10-22T08:00:00+09:00"
            )
            assert keyword_payload["candidate_count"] == 3
            assert keyword_payload["selected_count"] == 2
            assert [item["id"] for item in keyword_payload["items"]] == [
                row["id"] for row in selected
            ]
            assert {
                row["id"] for row in ai.select_article_ids.call_args.args[1]
            } == {
                row["id"] for row in articles
            }
            assert all(
                len(row["content_preview"]) == 600
                for row in ai.select_article_ids.call_args.args[1]
            )
            assert [
                row["content"]
                for row in ai.summarize_keyword.call_args.args[1]
            ] == [
                row["content"][:4000] for row in selected
            ]
            monkeypatch.setattr(
                briefings.settings, "redis_url", "redis://offline",
            )

            # Read grouped first: it must materialize actionable URL identities
            # even when /today has not populated any missing article rows.
            grouped = client.get(
                "/api/v1/briefings/today/grouped", headers=headers,
            )
            assert grouped.status_code == 200
            body = grouped.json()
            assert body["briefing_date"] == edition
            assert body["user_id"] == str(user_id)
            assert len(body["keywords"]) == 1
            block = body["keywords"][0]
            assert block["keyword"] == keyword
            assert block["headline"] == keyword_payload["headline"]
            assert block["summary"] == keyword_payload["summary"]
            assert [row["id"] for row in block["items"]] == expected_ids
            for row, produced in zip(block["items"], keyword_payload["items"]):
                assert row["summary"] == produced["summary"]
                assert row["url"] == produced["url"]
                assert row["image_url"] == produced["thumbnail_url"]

            for article_id in expected_ids:
                bookmark = client.put(
                    f"/api/v1/briefings/{article_id}/bookmark",
                    headers=headers,
                )
                feedback = client.post(
                    f"/api/v1/briefings/{article_id}/feedback",
                    headers=headers,
                    json={"feedback_type": "like"},
                )
                assert bookmark.status_code == feedback.status_code == 200
                assert bookmark.json()["article_id"] == article_id
                assert feedback.json()["article_id"] == article_id

            today = client.get("/api/v1/briefings/today", headers=headers)
            assert today.status_code == 200
            today_by_id = {row["id"]: row for row in today.json()["items"]}
            assert set(today_by_id) == set(expected_ids)
            for article_id, produced in zip(
                expected_ids, keyword_payload["items"],
            ):
                row = today_by_id[article_id]
                assert row["title"] == produced["title"]
                assert row["summary"] == produced["summary"]
                assert row["original_url"] == produced["url"]
                assert row["category"] == keyword
                assert row["is_bookmarked"] is True
                assert row["feedback_type"] == "like"
            updated = client.get(
                "/api/v1/briefings/today/grouped", headers=headers,
            )
            assert updated.status_code == 200
            assert all(
                row["is_bookmarked"] is True and row["feedback_type"] == "like"
                for row in updated.json()["keywords"][0]["items"]
            )
            assert cache.reads == [user_key, keyword_key, user_key]
            assert batch == original
            no_raw_query.assert_not_called()
            with engine.connect() as connection:
                stored = dict(connection.execute(text(
                    "SELECT id, content FROM articles"
                )).all())
            assert stored == {
                int(expected_ids[0]): selected[0]["content"],
                int(expected_ids[1]): "",
            }
    finally:
        engine.dispose()
