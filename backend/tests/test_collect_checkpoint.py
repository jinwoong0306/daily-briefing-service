import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


PIPELINE_DIR = Path(__file__).resolve().parents[1] / "pipeline"
BRIEFING_DATE = "2026-10-22"
WINDOW_START = datetime.fromisoformat("2026-10-21T20:00:00+09:00")
WINDOW_END = datetime.fromisoformat("2026-10-22T02:00:00+09:00")
ARTICLE = {
    "title": "Collected article",
    "link": "https://example.test/new",
    "pubDate": "2026-10-22T01:00:00+09:00",
    "fullText": "Persisted article body",
}


@pytest.fixture
def pipeline(monkeypatch, tmp_path):
    # Replace external boundaries only; execute the real orchestrator, crawler,
    # time filtering, merging, and filesystem persistence.
    monkeypatch.syspath_prepend(str(PIPELINE_DIR))
    external_modules = {
        "scraper": {"NaverNewsScraper": None},
        "clustering": {"run_pipeline": Mock()},
        "ai_briefing": {"generate_and_cache_briefings": Mock()},
        "push_delivery": {"deliver_cached_briefings": Mock()},
        "supabase_uploader": {
            "upload_articles_to_supabase": Mock(),
            "get_incremental_window_kst": Mock(
                return_value=(WINDOW_START, WINDOW_END, True)
            ),
            "start_pipeline_run": Mock(return_value=71),
            "finish_pipeline_run": Mock(),
            "fetch_user_keywords_from_supabase": Mock(return_value=["keyword"]),
        },
    }
    for name, attributes in external_modules.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)

    loaded = {}
    for name in ("staging_manager", "unified_crawler", "main"):
        spec = importlib.util.spec_from_file_location(
            name, PIPELINE_DIR / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        loaded[name] = module

    crawler = loaded["unified_crawler"]
    monkeypatch.setattr(crawler, "fetch_google_top", lambda: [dict(ARTICLE)])
    monkeypatch.setattr(crawler, "fetch_google_keyword", lambda keyword: [])
    monkeypatch.setattr(crawler, "fetch_naver_sim", lambda keyword: [])
    monkeypatch.setattr(crawler, "extract_full_text", lambda articles: articles)
    monkeypatch.setenv("PIPELINE_COLLECTION_START_HOUR", "20")
    monkeypatch.setenv("PIPELINE_COLLECTION_END_HOUR", "6")
    monkeypatch.setenv("COLLECTOR_PIPELINE_NAME", "collector_test")
    monkeypatch.chdir(tmp_path)
    return SimpleNamespace(
        main=loaded["main"],
        crawler=crawler,
        staging=loaded["staging_manager"],
        finish=sys.modules["supabase_uploader"].finish_pipeline_run,
        start=sys.modules["supabase_uploader"].start_pipeline_run,
    )


@pytest.mark.parametrize("empty", [False, True])
def test_collect_success_is_recorded_only_after_staging(pipeline, monkeypatch, empty):
    if empty:
        monkeypatch.setattr(pipeline.crawler, "fetch_google_top", lambda: [])

    def finish_after_persistence(*, run_id, status):
        assert run_id == 71
        assert status == "success"
        staged = pipeline.staging.load_staging(BRIEFING_DATE)
        assert [article["link"] for article in staged["articles"]] == (
            [] if empty else [ARTICLE["link"]]
        )
        assert staged["runs"][0]["window_end_kst"] == WINDOW_END.isoformat()

    pipeline.finish.side_effect = finish_after_persistence
    pipeline.main.run_collect_mode({})

    pipeline.finish.assert_called_once_with(run_id=71, status="success")
    assert pipeline.start.call_args.kwargs["pipeline_name"] == "collector_test"


@pytest.mark.parametrize("failure", ["serialize", "fsync", "replace"])
def test_staging_failure_preserves_checkpoint_and_previous_file(
    pipeline, monkeypatch, failure
):
    pipeline.staging.append_articles_to_staging(
        BRIEFING_DATE, [{"link": "https://example.test/old", "fullText": "Old body"}]
    )
    previous = pipeline.staging.load_staging(BRIEFING_DATE)
    error = OSError("injected staging failure")

    if failure == "serialize":
        def fail_dump(data, stream, **kwargs):
            stream.write("{")
            raise error
        monkeypatch.setattr(pipeline.staging.json, "dump", fail_dump)
    else:
        monkeypatch.setattr(
            pipeline.staging.os, failure, Mock(side_effect=error)
        )

    with pytest.raises(OSError, match="injected staging failure"):
        pipeline.main.run_collect_mode({})

    pipeline.finish.assert_called_once_with(
        run_id=71, status="failed", error_message=str(error)
    )
    assert pipeline.staging.load_staging(BRIEFING_DATE) == previous
    assert sorted(path.name for path in Path("cache/staging").iterdir()) == [
        f"{BRIEFING_DATE}.json"
    ]


def test_crawl_failure_records_failure_without_staging(pipeline, monkeypatch):
    monkeypatch.setattr(
        pipeline.crawler, "fetch_google_top",
        Mock(side_effect=RuntimeError("injected crawl failure")),
    )

    with pytest.raises(RuntimeError, match="injected crawl failure"):
        pipeline.main.run_collect_mode({})

    pipeline.finish.assert_called_once_with(
        run_id=71, status="failed", error_message="injected crawl failure"
    )
    assert not Path("cache/staging").exists()


def test_standalone_crawler_still_finishes_its_own_run(pipeline):
    result = pipeline.crawler.run_pipeline(
        ["keyword"], out_path=None, upload_to_db=False
    )

    assert result["articles"][0]["link"] == ARTICLE["link"]
    pipeline.finish.assert_called_once_with(run_id=71, status="success")
    assert not Path("cache/staging").exists()


def test_staging_flushes_file_before_atomic_replace(pipeline, monkeypatch):
    events = []
    real_fsync = pipeline.staging.os.fsync
    real_replace = pipeline.staging.os.replace

    def fsync(fd):
        events.append("fsync")
        return real_fsync(fd)

    def replace(source, destination):
        events.append("replace")
        return real_replace(source, destination)

    monkeypatch.setattr(pipeline.staging.os, "fsync", fsync)
    monkeypatch.setattr(pipeline.staging.os, "replace", replace)
    pipeline.staging.append_articles_to_staging(BRIEFING_DATE, [ARTICLE])

    assert events[:2] == ["fsync", "replace"]
    assert pipeline.staging.load_staging(BRIEFING_DATE)["articles"] == [ARTICLE]
