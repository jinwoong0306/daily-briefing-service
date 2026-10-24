"""Offline collection -> staging -> per-keyword edition regressions."""

from copy import deepcopy
from datetime import datetime
from importlib import import_module
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
crawler = import_module("unified_crawler")
staging = import_module("staging_manager")
clustering = import_module("clustering")
uploader = import_module("supabase_uploader")
main = import_module("main")
ai_briefing = import_module("ai_briefing")

EDITION = "2026-10-22"
TOP = "\uc8fc\uc694\uc774\uc288"
START = datetime.fromisoformat("2026-10-21T20:00:00+09:00")
END = datetime.fromisoformat("2026-10-22T06:00:00+09:00")


def article(keyword="AI", **overrides):
    return {
        "keyword": keyword,
        "title": "Shared event",
        "link": "https://example.test/shared",
        "fullText": "Original body.",
        "pubDate": "2026-10-22T01:55:00+09:00",
        "source_type": "test",
        **overrides,
    }


class RecordingDB:
    def __init__(self):
        self.writes = []

    def table(self, table):
        self.table_name = table
        return self

    def upsert(self, rows, on_conflict):
        columns = [column.strip() for column in on_conflict.split(",")]
        identities = [tuple(row[column] for column in columns) for row in rows]
        assert len(identities) == len(set(identities))
        self.writes.append((self.table_name, deepcopy(rows), on_conflict))
        return self

    def execute(self):
        return SimpleNamespace(data=[])


@pytest.fixture
def offline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIPELINE_COLLECTION_START_HOUR", "20")
    monkeypatch.setenv("PIPELINE_COLLECTION_END_HOUR", "6")
    monkeypatch.setenv("SUPABASE_ARTICLES_TABLE", "articles")
    monkeypatch.setenv("SUPABASE_ARTICLES_CONFLICT_COL", "url")
    monkeypatch.setenv("SUPABASE_CLUSTERED_TABLE", "articles")
    monkeypatch.setenv("SUPABASE_CLUSTERED_CONFLICT_COL", "url")
    db = RecordingDB()
    monkeypatch.setattr(uploader, "get_supabase_client", lambda: db)
    return db


@pytest.mark.parametrize("duplicate", [
    article("Tech"),
    article("Tech", link="https://example.test/alternate"),
])
def test_deduplication_retains_associations_and_first_original(duplicate):
    source = [article(), duplicate, article("AI")]
    before = deepcopy(source)
    result = crawler.deduplicate_news(source)
    assert len(result) == 1
    assert result[0] == {**source[0], "keywords": ["AI", "Tech"]}
    assert source == before
    assert crawler.deduplicate_news(result) == result


def test_url_title_bridge_and_later_alias_keep_all_associations():
    source = [
        article("AI", title="First", link="https://example.test/first"),
        article("Tech", title="Second", link="https://example.test/second"),
        article("Space", title="Second", link="https://example.test/first"),
        article("Science", title="Third", link="https://example.test/second"),
    ]
    result = crawler.deduplicate_news(source)
    assert result == [{
        **source[0], "keywords": ["AI", "Tech", "Space", "Science"],
    }]


@pytest.mark.parametrize("later_body", ["Short", "Original body.", "Longer body." * 20])
def test_overlapping_staging_runs_union_keywords_independently_of_body(
    offline, later_body
):
    first = crawler.deduplicate_news([article(TOP), article("AI")])
    second = [article("Tech", fullText=later_body)]
    before = deepcopy((first, second))
    staging.append_articles_to_staging(
        EDITION, first, START,
        datetime.fromisoformat("2026-10-22T02:00:00+09:00"),
    )
    overlap_start = datetime.fromisoformat("2026-10-22T01:50:00+09:00")
    staging.append_articles_to_staging(EDITION, second, overlap_start, END)
    staging.append_articles_to_staging(EDITION, second, overlap_start, END)
    saved = staging.load_staging(EDITION)
    assert len(saved["articles"]) == 1
    assert saved["articles"][0]["keywords"] == [TOP, "AI", "Tech"]
    assert saved["articles"][0]["keyword"] == TOP
    assert saved["articles"][0]["fullText"] == max(
        [first[0]["fullText"], later_body], key=len
    )
    assert len(saved["runs"]) == 3
    assert (first, second) == before


@pytest.mark.parametrize("google_top_first", [False, True])
def test_collect_and_brief_cli_produce_actual_representatives_for_each_keyword(
    offline, monkeypatch, google_top_first
):
    shared = article()
    ai_only = article(
        title="Detailed event", link="https://example.test/detailed",
        fullText="Original event with longer details." * 10,
    )
    tech_only = article(
        "Tech", title="Unrelated event", link="https://example.test/unrelated",
        fullText="An unrelated event.",
    )
    monkeypatch.setattr(
        crawler, "fetch_google_top",
        lambda: [deepcopy(shared)] if google_top_first else [],
    )
    monkeypatch.setattr(
        crawler, "fetch_google_keyword",
        lambda keyword: deepcopy(
            [shared, ai_only] if keyword == "AI" else [shared, tech_only]
        ),
    )
    monkeypatch.setattr(crawler, "fetch_naver_sim", lambda keyword: [])
    scrape = Mock(side_effect=lambda rows: rows)
    monkeypatch.setattr(crawler, "extract_full_text", scrape)
    collected = crawler.run_pipeline(
        ["AI", "Tech"], explicit_window=(START, END),
        out_path=None, upload_to_db=False, record_run=False,
    )
    assert len(scrape.call_args.args[0]) == 3
    assert collected["articles"][0]["keywords"] == (
        [TOP, "AI", "Tech"] if google_top_first else ["AI", "Tech"]
    )
    originals = deepcopy(collected["articles"])
    staging.append_articles_to_staging(EDITION, originals, START, END)

    vector_by_body = {
        shared["fullText"]: [1.0, 0.0],
        ai_only["fullText"]: [0.999, 0.001],
        tech_only["fullText"]: [0.0, 1.0],
    }
    embeddings = Mock(side_effect=lambda texts: np.array([
        vector_by_body[text] for text in texts
    ]))
    monkeypatch.setattr(clustering, "get_embeddings", embeddings)
    monkeypatch.setattr(clustering, "visualize_clusters", Mock())
    ai = ai_briefing.PlaceholderBriefingAI()
    selections = Mock(wraps=ai.select_article_ids)
    monkeypatch.setattr(ai, "select_article_ids", selections)
    monkeypatch.setattr(ai_briefing, "OpenAIBriefingAI", lambda: ai)
    monkeypatch.setattr(
        ai_briefing, "extract_thumbnail_url", Mock(return_value={})
    )
    monkeypatch.setattr(
        ai_briefing, "fetch_user_keyword_subscriptions",
        lambda table: [
            {"user_id": "reader", "keyword": keyword}
            for keyword in ["AI", "Tech"]
        ],
    )
    raw_query = Mock(side_effect=AssertionError("No raw DB fallback"))
    monkeypatch.setattr(
        ai_briefing, "fetch_recent_articles_for_keyword", raw_query
    )
    cache = {}

    def save(key, payload, ttl):
        cache[key] = deepcopy(payload)
        return {"saved": True}

    monkeypatch.setattr(ai_briefing, "set_json", save)
    monkeypatch.setattr(main, "load_config", lambda **kwargs: {})
    monkeypatch.setattr(main, "acquire_process_lock", lambda path: Mock())
    monkeypatch.setattr(sys, "argv", ["main.py", "brief", "--date", EDITION])
    main.main()

    selected = {
        call.args[0]: {row["id"] for row in call.args[1]}
        for call in selections.call_args_list
    }
    assert selected == {
        "AI": {ai_only["link"]},
        "Tech": {shared["link"], tech_only["link"]},
    }
    assert embeddings.call_count == 2
    for keyword, expected in selected.items():
        payload = cache[ai_briefing.build_keyword_briefing_key(EDITION, keyword)]
        assert payload["candidate_source"] == "cluster_representatives"
        assert payload["briefing_date"] == EDITION
        assert payload["candidate_count"] == len(expected)
        assert {row["id"] for row in payload["items"]} == expected
    assert staging.load_staging(EDITION)["articles"] == originals
    raw_query.assert_not_called()
    assert len(offline.writes) == 1
    assert offline.writes[0][2] == "url"
    assert len(offline.writes[0][1]) == 3


def test_expansion_keeps_source_count_and_legacy_scalar_payload(offline):
    source = {
        "meta": {"briefing_date": EDITION},
        "articles": [article(keywords=["AI", " Tech ", "Tech"])],
    }
    batch = clustering.run_pipeline(source)
    assert batch["source_count"] == 1
    assert [(row["keyword"], row["url"]) for row in batch["articles"]] == [
        ("AI", source["articles"][0]["link"]),
        ("Tech", source["articles"][0]["link"]),
    ]
    legacy = article()
    assert crawler.deduplicate_news([legacy]) == [legacy]
    staging.append_articles_to_staging(EDITION, [legacy, legacy])
    assert staging.load_staging(EDITION)["articles"] == [legacy]
    assert clustering.run_pipeline({
        "meta": {"briefing_date": EDITION}, "articles": [legacy],
    })["articles"][0]["keyword"] == "AI"


def test_raw_upload_keeps_unique_url_scalar_contract(offline):
    row = article(keywords=["AI", "Tech"])
    result = uploader.upload_articles_to_supabase([row])
    assert result == {"enabled": True, "uploaded": 1, "prepared": 1}
    table, rows, conflict = offline.writes[0]
    assert (table, conflict) == ("articles", "url")
    assert rows == [{
        "keyword": "AI", "source_type": "test", "title": row["title"],
        "content": row["fullText"], "url": row["link"],
        "pub_date": row["pubDate"],
    }]


@pytest.mark.parametrize("conflict, expected_count", [("url", 1), ("url,keyword", 2)])
def test_clustered_upload_respects_configured_conflict_without_mutating_candidates(
    offline, monkeypatch, conflict, expected_count
):
    monkeypatch.setenv("SUPABASE_CLUSTERED_CONFLICT_COL", conflict)
    source = article()
    grouped = {
        keyword: [{
            "keyword": keyword, "title": source["title"], "link": source["link"],
            "content": source["fullText"], "pubDate": source["pubDate"],
            "source": "test",
        }]
        for keyword in ["AI", "Tech"]
    }
    before = deepcopy(grouped)
    result = uploader.upload_clustered_result_to_supabase(grouped, batch_size=1)
    assert result["prepared"] == result["uploaded"] == expected_count
    assert len(offline.writes) == expected_count
    assert offline.writes[0][1][0]["keyword"] == "AI"
    assert all(write[2] == conflict for write in offline.writes)
    assert grouped == before
