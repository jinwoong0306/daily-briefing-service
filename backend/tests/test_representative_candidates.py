"""Offline tests of the real clustering -> edition -> AI -> cache handoff."""

from copy import deepcopy
from importlib import import_module
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
ai_briefing = import_module("ai_briefing")
clustering = import_module("clustering")
main = import_module("main")
staging = import_module("staging_manager")

EDITION = "2026-10-22"


def article(name, body, published="2026-10-22T03:00:00+09:00"):
    return {
        "keyword": "science",
        "title": name,
        "link": f"https://example.test/{name}",
        "fullText": body,
        "pubDate": published,
        "source_type": "test",
    }


class RecordingAI(ai_briefing.PlaceholderBriefingAI):
    def __init__(self):
        self.selections = []
        self.summaries = []

    def select_article_ids(
        self, keyword, selection_inputs, min_items, max_items
    ):
        self.selections.append(deepcopy(selection_inputs))
        return super().select_article_ids(
            keyword, selection_inputs, min_items, max_items
        )

    def summarize_keyword(self, keyword, summary_inputs):
        self.summaries.append(deepcopy(summary_inputs))
        return super().summarize_keyword(keyword, summary_inputs)


@pytest.fixture
def pipeline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIPELINE_COLLECTION_START_HOUR", "20")
    monkeypatch.setenv("PIPELINE_COLLECTION_END_HOUR", "6")
    monkeypatch.setenv("BRIEFING_CANDIDATE_LIMIT", "30")
    monkeypatch.setenv("BRIEFING_MIN_ITEMS_PER_KEYWORD", "3")
    monkeypatch.setenv("BRIEFING_MAX_ITEMS_PER_KEYWORD", "5")
    monkeypatch.setenv("BRIEFING_SELECTION_PREVIEW_CHARS", "600")
    monkeypatch.setenv("BRIEFING_SUMMARY_CONTENT_CHARS", "4000")
    raw = [
        article("launch-short", "Satellite launch succeeds."),
        article("launch-long", "Satellite launch succeeds. Details. " * 150),
        article("unrelated", "A new fossil species is discovered."),
    ]
    # Only the remote embedding API is replaced. Real cosine/average-linkage
    # clustering and longest-body representative selection run below.
    vector_by_preview = {
        raw[0]["fullText"][:4000]: [1.0, 0.0, 0.0],
        raw[1]["fullText"][:4000]: [0.999, 0.001, 0.0],
        raw[2]["fullText"][:4000]: [0.0, 0.0, 1.0],
    }
    embeddings = Mock(side_effect=lambda texts: np.array([
        vector_by_preview[text] for text in texts
    ]))
    monkeypatch.setattr(clustering, "get_embeddings", embeddings)
    monkeypatch.setattr(clustering, "visualize_clusters", Mock())
    monkeypatch.setattr(
        clustering, "upload_clustered_result_to_supabase",
        Mock(return_value={"enabled": False}),
    )
    ai = RecordingAI()
    monkeypatch.setattr(ai_briefing, "OpenAIBriefingAI", lambda: ai)
    monkeypatch.setattr(
        ai_briefing, "extract_thumbnail_url",
        Mock(return_value={"thumbnail_status": "missing"}),
    )
    monkeypatch.setattr(
        ai_briefing, "fetch_user_keyword_subscriptions",
        Mock(return_value=[{"user_id": "user-1", "keyword": "science"}]),
    )
    raw_query = Mock(side_effect=AssertionError("Raw DB query is forbidden"))
    monkeypatch.setattr(
        ai_briefing, "fetch_recent_articles_for_keyword", raw_query
    )
    cache = {}

    def save(key, payload, ttl):
        cache[key] = deepcopy(payload)
        return {"saved": True}

    monkeypatch.setattr(ai_briefing, "set_json", save)
    upload = Mock(return_value={"enabled": True, "uploaded": 3, "prepared": 3})
    monkeypatch.setattr(main, "upload_articles_to_supabase", upload)
    monkeypatch.setattr(main, "start_pipeline_run", Mock(return_value=17))
    finish = Mock()
    monkeypatch.setattr(main, "finish_pipeline_run", finish)
    return SimpleNamespace(
        raw=raw, ai=ai, embeddings=embeddings, cache=cache,
        upload=upload, finish=finish, raw_query=raw_query,
    )


def stage(raw, edition=EDITION):
    staging.append_articles_to_staging(edition, deepcopy(raw))


def test_real_brief_uses_two_representatives_and_preserves_all_source_bodies(
    pipeline,
):
    original = deepcopy(pipeline.raw)
    stage(original)
    # An unrelated cache file and another staged edition must not be scanned.
    stage([article("historical", "Old body")], "2026-10-21")
    staging.append_articles_to_staging(
        "stale-cache", [article("stale", "Never embed this")],
        staging_dir="cache",
    )

    main.run_finalize_mode({}, EDITION)
    pipeline.upload.assert_called_once_with(original)
    pipeline.finish.assert_called_once_with(run_id=17, status="success")
    main.run_brief_mode(EDITION)

    assert pipeline.embeddings.call_count == 2
    expected = {original[1]["link"], original[2]["link"]}
    assert {row["id"] for row in pipeline.ai.selections[0]} == expected
    assert {row["id"] for row in pipeline.ai.summaries[0]} == expected
    assert max(len(row["content_preview"]) for row in
               pipeline.ai.selections[0]) == 600
    assert max(len(row["content"]) for row in
               pipeline.ai.summaries[0]) == 4000
    assert staging.load_staging(EDITION)["articles"] == original
    assert len(pipeline.upload.call_args.args[0][1]["fullText"]) > 4000
    pipeline.raw_query.assert_not_called()
    keyword_key = ai_briefing.build_keyword_briefing_key(EDITION, "science")
    user_key = ai_briefing.build_user_briefing_key(EDITION, "user-1")
    keyword_payload = pipeline.cache[keyword_key]
    assert keyword_payload["candidate_source"] == "cluster_representatives"
    assert keyword_payload["candidate_count"] == 2
    assert keyword_payload["selected_count"] == 2
    assert {row["id"] for row in keyword_payload["items"]} == expected
    assert pipeline.cache[user_key]["keywords"] == [keyword_payload]


def test_candidates_are_filtered_to_edition_before_embedding(pipeline):
    source = {
        "meta": {"briefing_date": EDITION},
        "articles": pipeline.raw + [
            article("old", "Out of window", "2026-10-21T19:59:59+09:00"),
            article("new", "Out of window", "2026-10-22T06:00:01+09:00"),
        ],
    }
    batch = clustering.run_pipeline(source)
    assert batch["source_count"] == 3
    assert len(batch["articles"]) == 2
    assert len(pipeline.embeddings.call_args.args[0]) == 3
    assert len(source["articles"]) == 5


def test_same_event_remains_available_for_each_keyword(pipeline):
    other_keyword = deepcopy(pipeline.raw[1])
    other_keyword["keyword"] = "space"
    batch = clustering.run_pipeline({
        "meta": {"briefing_date": EDITION},
        "articles": pipeline.raw + [other_keyword],
    })
    assert [(row["keyword"], row["url"]) for row in batch["articles"]] == [
        ("science", pipeline.raw[1]["link"]),
        ("science", pipeline.raw[2]["link"]),
        ("space", other_keyword["link"]),
    ]


@pytest.mark.parametrize("failure", ["embedding", "clustering", "missing"])
def test_failed_clustering_does_not_reuse_previous_report_or_cache(
    pipeline, monkeypatch, failure
):
    stage(pipeline.raw)
    main.run_brief_mode(EDITION)
    pipeline.cache.clear()
    pipeline.ai.selections.clear()
    assert Path("cache/clustered_result.json").exists()
    if failure == "embedding":
        monkeypatch.setattr(
            clustering, "get_embeddings", Mock(return_value=np.array([]))
        )
    elif failure == "clustering":
        monkeypatch.setattr(
            clustering, "AgglomerativeClustering",
            Mock(side_effect=RuntimeError("injected model failure")),
        )
    else:
        monkeypatch.setattr(
            clustering, "cluster_and_extract", Mock(return_value=[])
        )

    with pytest.raises(RuntimeError):
        main.run_brief_mode(EDITION)

    assert pipeline.cache == {}
    assert pipeline.ai.selections == []
    pipeline.raw_query.assert_not_called()


def test_finalize_failure_never_marks_staging_or_run_success(
    pipeline, monkeypatch
):
    stage(pipeline.raw)
    monkeypatch.setattr(
        main, "run_clustering_pipeline", Mock(return_value=None)
    )
    with pytest.raises(ValueError, match="Successful representative"):
        main.run_finalize_mode({}, EDITION)
    assert staging.load_staging(EDITION)["meta"]["finalized_at"] is None
    pipeline.upload.assert_not_called()
    assert pipeline.finish.call_args.kwargs["status"] == "failed"


@pytest.mark.parametrize("problem", [
    "wrong-edition", "failed", "missing", "outside-window", "raw-source",
])
def test_generation_rejects_invalid_batch_before_ai_or_cache(
    pipeline, problem
):
    batch = clustering.run_pipeline({
        "meta": {"briefing_date": EDITION}, "articles": pipeline.raw,
    })
    if problem == "wrong-edition":
        batch["briefing_date"] = "2026-10-21"
    elif problem == "failed":
        batch["status"] = "failed"
    elif problem == "missing":
        batch["articles"] = []
    elif problem == "outside-window":
        batch["articles"][0]["pub_date"] = "2026-10-21T19:59:59+09:00"
    else:
        batch["candidate_source"] = "raw_articles"
    with pytest.raises(ValueError):
        ai_briefing.generate_and_cache_briefings(
            EDITION, candidate_batch=batch
        )
    assert pipeline.ai.selections == []
    assert pipeline.cache == {}
    pipeline.raw_query.assert_not_called()


def test_generation_requires_candidate_input(pipeline):
    with pytest.raises(TypeError):
        ai_briefing.generate_and_cache_briefings(EDITION)
    with pytest.raises(ValueError):
        ai_briefing.generate_and_cache_briefings(EDITION, candidate_batch=None)
    assert pipeline.cache == {}


def test_missing_edition_never_uses_historical_staging(pipeline):
    stage(pipeline.raw, "2026-10-21")
    with pytest.raises(ValueError, match="No staged articles"):
        main.run_brief_mode(EDITION)
    pipeline.embeddings.assert_not_called()
    assert pipeline.cache == {}


def test_wrong_staging_metadata_is_rejected(pipeline, monkeypatch):
    monkeypatch.setattr(main, "load_staging", Mock(return_value={
        "meta": {"briefing_date": "2026-10-21"}, "articles": pipeline.raw,
    }))
    with pytest.raises(ValueError, match="Staged source edition mismatch"):
        main.run_brief_mode(EDITION)
    pipeline.embeddings.assert_not_called()


def test_full_mode_passes_current_crawl_not_disk_cache(pipeline, monkeypatch):
    collected = {
        "meta": {"window_end_kst": "2026-10-22T06:00:00+09:00"},
        "articles": pipeline.raw,
    }
    monkeypatch.setattr(main, "resolve_keywords", lambda config: (
        ["science"], "test"
    ))
    monkeypatch.setattr(
        main, "run_unified_pipeline", lambda keywords: collected
    )
    stage([article("old", "Do not embed")], "2026-10-21")
    main.run_full_mode({})
    assert collected["meta"]["briefing_date"] == EDITION
    assert len(pipeline.embeddings.call_args.args[0]) == 3


def test_historical_brief_uses_requested_edition(pipeline):
    historical = deepcopy(pipeline.raw)
    for row in historical:
        row["pubDate"] = "2024-02-29T21:00:00+09:00"
    stage(historical, "2024-03-01")
    stage(pipeline.raw)
    main.run_brief_mode("2024-03-01")
    assert len(pipeline.ai.selections[0]) == 2
    assert all(
        row["pub_date"] == "2024-02-29T21:00:00+09:00"
        for row in pipeline.ai.selections[0]
    )
    assert all(
        payload["briefing_date"] == "2024-03-01"
        for payload in pipeline.cache.values()
    )


def test_report_upload_failure_is_not_silent_success(pipeline, monkeypatch):
    stage(pipeline.raw)
    monkeypatch.setattr(
        clustering, "upload_clustered_result_to_supabase",
        Mock(side_effect=RuntimeError("injected report upload failure")),
    )
    with pytest.raises(RuntimeError, match="injected report upload failure"):
        main.run_brief_mode(EDITION)
    assert pipeline.ai.selections == []
    assert pipeline.cache == {}
