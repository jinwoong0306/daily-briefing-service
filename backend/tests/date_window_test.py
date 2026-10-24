"""Run with: python -m unittest discover -s backend/tests -p '*_test.py'."""

import os
from datetime import datetime
from importlib import import_module
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
ai_briefing = import_module("ai_briefing")


class FakeQuery:
    """Execute the recorded query against timestamped rows, without a network."""

    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def select(self, fields):
        self.calls.append(("select", fields))
        return self

    def eq(self, field, value):
        self.calls.append(("eq", field, value))
        return self

    def neq(self, field, value):
        self.calls.append(("neq", field, value))
        return self

    def gte(self, field, value):
        self.calls.append(("gte", field, value))
        return self

    def lte(self, field, value):
        self.calls.append(("lte", field, value))
        return self

    def order(self, field, desc=False):
        self.calls.append(("order", field, desc))
        return self

    def limit(self, count):
        self.calls.append(("limit", count))
        return self

    def execute(self):
        rows = list(self.rows)
        for operation, *args in self.calls:
            if operation == "eq":
                field, value = args
                rows = [row for row in rows if row[field] == value]
            elif operation == "neq":
                field, value = args
                rows = [row for row in rows if row[field] is not None and row[field] != value]
            elif operation in ("gte", "lte"):
                field, value = args
                bound = datetime.fromisoformat(value)
                rows = [
                    row for row in rows
                    if (
                        datetime.fromisoformat(row[field]) >= bound
                        if operation == "gte"
                        else datetime.fromisoformat(row[field]) <= bound
                    )
                ]
            elif operation == "order":
                field, desc = args
                rows.sort(
                    key=lambda row: datetime.fromisoformat(row[field]),
                    reverse=desc,
                )
            elif operation == "limit":
                rows = rows[:args[0]]
        return SimpleNamespace(data=rows)


class FakeSupabase:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def table(self, name):
        query = FakeQuery(self.rows)
        self.queries.append((name, query))
        return query


class RecordingAI(ai_briefing.PlaceholderBriefingAI):
    def select_article_ids(self, keyword, selection_inputs, min_items, max_items):
        self.selection_inputs = selection_inputs
        return super().select_article_ids(
            keyword, selection_inputs, min_items, max_items
        )

    def summarize_keyword(self, keyword, summary_inputs):
        self.summary_inputs = summary_inputs
        return super().summarize_keyword(keyword, summary_inputs)


def article(article_id, pub_date, keyword="science"):
    return {
        "id": article_id,
        "keyword": keyword,
        "title": f"Article {article_id}",
        "url": f"https://example.test/{article_id}",
        "content": "Article content",
        "pub_date": pub_date,
        "source_type": "test",
    }


class DateWindowTest(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            "PIPELINE_COLLECTION_START_HOUR": "20",
            "PIPELINE_COLLECTION_END_HOUR": "6",
            "BRIEFING_CANDIDATE_LIMIT": "30",
            "BRIEFING_MIN_ITEMS_PER_KEYWORD": "1",
            "BRIEFING_MAX_ITEMS_PER_KEYWORD": "5",
            "SUPABASE_ARTICLES_TABLE": "articles",
        })
        env.start()
        self.addCleanup(env.stop)

    def test_inclusive_kst_boundaries_compare_publication_instants(self):
        client = FakeSupabase([
            article("stale", "2026-04-04T10:59:59.999999+00:00"),
            article("start", "2026-04-04T20:00:00+09:00"),
            article("middle", "2026-04-04T17:00:00+00:00"),
            article("end", "2026-04-04T21:00:00+00:00"),
            article("future", "2026-04-05T06:00:00.000001+09:00"),
            article("other-keyword", "2026-04-05T01:00:00+09:00", "sports"),
        ])
        with patch.object(ai_briefing, "get_supabase_client", return_value=client):
            rows = ai_briefing.fetch_recent_articles_for_keyword(
                "science", 30, "2026-04-05", "edition_articles"
            )

        self.assertEqual([row["id"] for row in rows], ["end", "middle", "start"])
        table, query = client.queries[0]
        self.assertEqual(table, "edition_articles")
        self.assertIn(("gte", "pub_date", "2026-04-04T20:00:00+09:00"), query.calls)
        self.assertIn(("lte", "pub_date", "2026-04-05T06:00:00+09:00"), query.calls)

    def test_window_filters_before_candidate_limit(self):
        client = FakeSupabase([
            article("later-1", "2026-04-06T06:00:00+09:00"),
            article("later-2", "2026-04-06T05:00:00+09:00"),
            article("latest-valid", "2026-04-05T06:00:00+09:00"),
            article("earlier-valid", "2026-04-05T04:00:00+09:00"),
            article("stale", "2026-04-04T19:59:59+09:00"),
        ])
        with patch.object(ai_briefing, "get_supabase_client", return_value=client):
            rows = ai_briefing.fetch_recent_articles_for_keyword(
                "science", 1, "2026-04-05"
            )

        self.assertEqual([row["id"] for row in rows], ["latest-valid"])

    def test_historical_reruns_only_send_edition_candidates_to_ai(self):
        for edition, previous_day in [
            ("2026-01-01", "2025-12-31"),
            ("2024-03-01", "2024-02-29"),
        ]:
            with self.subTest(edition=edition):
                client = FakeSupabase([
                    article("stale", f"{previous_day}T19:59:59+09:00"),
                    article("evening", f"{previous_day}T20:00:00+09:00"),
                    article("morning", f"{edition}T06:00:00+09:00"),
                    article("after-edition", f"{edition}T06:00:01+09:00"),
                    article("current-news", "2030-10-22T05:00:00+09:00"),
                ])
                ai = RecordingAI()
                with (
                    patch.object(ai_briefing, "get_supabase_client", return_value=client),
                    patch.object(ai_briefing, "extract_thumbnail_url", return_value={}),
                    patch.object(ai_briefing, "datetime", wraps=datetime) as clock,
                ):
                    clock.now.return_value = ai_briefing.KST.localize(
                        datetime(2030, 10, 22, 6, 30)
                    )
                    payload = ai_briefing.build_keyword_briefing(
                        "science", edition, ai=ai
                    )

                expected_ids = ["morning", "evening"]
                self.assertEqual(payload["briefing_date"], edition)
                self.assertEqual(payload["candidate_count"], 2)
                self.assertEqual(payload["selected_count"], 2)
                self.assertEqual(
                    [row["id"] for row in ai.selection_inputs], expected_ids
                )
                self.assertEqual(
                    [row["id"] for row in ai.summary_inputs], expected_ids
                )
                self.assertEqual(
                    [row["id"] for row in payload["items"]], expected_ids
                )

    def test_collection_hour_overrides_define_same_edition(self):
        client = FakeSupabase([
            article("too-early", "2026-04-04T21:59:59+09:00"),
            article("start", "2026-04-04T22:00:00+09:00"),
            article("end", "2026-04-05T04:00:00+09:00"),
            article("too-late", "2026-04-05T04:00:01+09:00"),
        ])
        with (
            patch.dict(os.environ, {
                "PIPELINE_COLLECTION_START_HOUR": "22",
                "PIPELINE_COLLECTION_END_HOUR": "4",
            }),
            patch.object(ai_briefing, "get_supabase_client", return_value=client),
        ):
            rows = ai_briefing.fetch_recent_articles_for_keyword(
                "science", 30, "2026-04-05"
            )

        self.assertEqual([row["id"] for row in rows], ["end", "start"])

    def test_empty_edition_does_not_backfill_from_other_dates(self):
        client = FakeSupabase([
            article("old", "2026-04-03T05:00:00+09:00"),
            article("new", "2026-04-06T05:00:00+09:00"),
        ])
        ai = RecordingAI()
        with (
            patch.object(ai_briefing, "get_supabase_client", return_value=client),
            patch.object(ai_briefing, "extract_thumbnail_url") as thumbnail,
        ):
            payload = ai_briefing.build_keyword_briefing(
                "science", "2026-04-05", ai=ai
            )

        self.assertEqual(ai.selection_inputs, [])
        self.assertEqual(ai.summary_inputs, [])
        self.assertEqual(payload["candidate_count"], 0)
        self.assertEqual(payload["selected_count"], 0)
        self.assertEqual(payload["items"], [])
        thumbnail.assert_not_called()

    def test_metadata_only_cache_rows_never_enter_selection(self):
        cached = article("cache-only", "2026-04-05T02:00:00+09:00")
        cached["content"] = ""
        client = FakeSupabase([
            cached,
            article("source", "2026-04-05T01:00:00+09:00"),
        ])
        with patch.object(ai_briefing, "get_supabase_client", return_value=client):
            rows = ai_briefing.fetch_recent_articles_for_keyword(
                "science", 1, "2026-04-05"
            )

        self.assertEqual([row["id"] for row in rows], ["source"])
        self.assertIn(("neq", "content", ""), client.queries[0][1].calls)


if __name__ == "__main__":
    unittest.main()
