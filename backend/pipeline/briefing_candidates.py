"""Edition boundaries and the in-memory representative candidate contract."""

import os
from datetime import datetime, timedelta

import pytz
from dateutil import parser as date_parser


KST = pytz.timezone("Asia/Seoul")


def edition_window(briefing_date: str) -> tuple[datetime, datetime]:
    edition_day = datetime.strptime(briefing_date, "%Y-%m-%d")

    def hour(name: str, default: int) -> int:
        try:
            return int(os.environ.get(name, str(default)))
        except ValueError:
            return default

    return (
        KST.localize((edition_day - timedelta(days=1)).replace(
            hour=hour("PIPELINE_COLLECTION_START_HOUR", 20)
        )),
        KST.localize(edition_day.replace(
            hour=hour("PIPELINE_COLLECTION_END_HOUR", 6)
        )),
    )


def publication_in_edition(value: str, briefing_date: str) -> bool:
    start, end = edition_window(briefing_date)
    try:
        published = date_parser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return False
    if published.tzinfo is None:
        published = KST.localize(published)
    return start <= published <= end


def validate_candidate_batch(batch: dict, briefing_date: str) -> list[dict]:
    """Reject missing representatives instead of backfilling with raw rows."""
    edition_window(briefing_date)
    if not isinstance(batch, dict) or batch.get("status") != "success":
        raise ValueError(
            "Successful representative candidate batch is required"
        )
    if batch.get("briefing_date") != briefing_date:
        raise ValueError("Representative candidate edition mismatch")
    if batch.get("candidate_source") != "cluster_representatives":
        raise ValueError("Representative candidate source is required")
    articles = batch.get("articles")
    if not isinstance(articles, list) or not articles:
        raise ValueError("Representative candidates are missing")
    seen = set()
    for article in articles:
        if not isinstance(article, dict) or not all(
            article.get(field)
            for field in (
                "id", "keyword", "title", "url", "content", "pub_date"
            )
        ):
            raise ValueError("Representative candidate is incomplete")
        key = (article["keyword"], str(article["id"]))
        if key in seen:
            raise ValueError("Duplicate representative candidate identity")
        seen.add(key)
        if not publication_in_edition(article["pub_date"], briefing_date):
            raise ValueError("Representative candidate is outside its edition")
    return articles
