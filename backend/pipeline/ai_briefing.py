"""
Build personalized news briefings and cache them in Redis.

News selection and final summaries use one configured OpenAI model.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Protocol

import pytz
from dateutil import parser as date_parser

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from redis_cache import (
    build_keyword_briefing_key,
    build_user_briefing_key,
    set_json,
)
from supabase_uploader import (
    fetch_user_keyword_subscriptions,
    get_supabase_client,
)


KST = pytz.timezone("Asia/Seoul")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _load_env_if_exists() -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("'").strip('"')


def _parse_pub_date(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=pytz.UTC)
    try:
        dt = date_parser.parse(value)
    except Exception:
        return datetime.min.replace(tzinfo=pytz.UTC)
    if dt.tzinfo is None:
        return KST.localize(dt)
    return dt


def _clean_article(row: dict) -> Optional[dict]:
    title = str(row.get("title") or "").strip()
    url = str(row.get("url") or "").strip()
    if not title or not url:
        return None

    content = str(row.get("content") or "").strip()
    return {
        "id": row.get("id"),
        "keyword": str(row.get("keyword") or "").strip(),
        "title": title,
        "url": url,
        "content": content,
        "pub_date": row.get("pub_date"),
        "source_type": row.get("source_type"),
    }


class BriefingAI(Protocol):
    model_status: str
    model: str

    def select_article_ids(
        self,
        keyword: str,
        selection_inputs: list[dict],
        min_items: int,
        max_items: int,
    ) -> list:
        ...

    def summarize_keyword(self, keyword: str, summary_inputs: list[dict]) -> dict:
        ...


def _article_for_selection(article: dict, max_chars: int) -> dict:
    content = article.get("content") or ""
    return {
        "id": str(article.get("id")),
        "title": article.get("title"),
        "pub_date": article.get("pub_date"),
        "source_type": article.get("source_type"),
        "content_preview": content[:max_chars],
    }


def _article_for_summary(article: dict, max_chars: int) -> dict:
    content = article.get("content") or ""
    return {
        "id": str(article.get("id")),
        "title": article.get("title"),
        "url": article.get("url"),
        "pub_date": article.get("pub_date"),
        "source_type": article.get("source_type"),
        "content": content[:max_chars],
    }


def _extract_chat_json(response) -> dict:
    content = response.choices[0].message.content or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"OpenAI response was not valid JSON: {content[:500]}") from e


class OpenAIBriefingAI:
    """
    GPT-5 nano briefing adapter.

    Stage 1 selects article IDs using titles and short previews.
    Stage 2 summarizes only the selected articles.
    """

    def __init__(self, model: Optional[str] = None):
        _load_env_if_exists()

        if OpenAI is None:
            raise RuntimeError("openai package is not installed. Run: pip install openai")

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for briefing generation")

        self.model = model or os.environ.get("OPENAI_BRIEFING_MODEL", "gpt-5-nano").strip() or "gpt-5-nano"
        self.model_status = "configured"
        self.client = OpenAI(api_key=api_key)
        self.reasoning_effort = os.environ.get("OPENAI_BRIEFING_REASONING_EFFORT", "low").strip() or "low"
        self.verbosity = os.environ.get("OPENAI_BRIEFING_VERBOSITY", "low").strip() or "low"

    def _json_completion(self, system_prompt: str, user_payload: dict, max_completion_tokens: int) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=self.reasoning_effort,
            verbosity=self.verbosity,
        )
        return _extract_chat_json(response)

    def select_article_ids(
        self,
        keyword: str,
        selection_inputs: list[dict],
        min_items: int,
        max_items: int,
    ) -> list:
        if not selection_inputs:
            return []

        system_prompt = (
            "You are a Korean news briefing editor. Select the most important, "
            "non-duplicative articles for the keyword. Return only JSON with "
            "selected_ids as an array, no prose."
        )
        payload = {
            "keyword": keyword,
            "min_items": min_items,
            "max_items": max_items,
            "selection_rules": [
                "Prefer high-impact, recent, non-duplicative articles.",
                "Avoid near-identical articles covering the same event unless the angle is meaningfully different.",
                "Return article IDs exactly as provided.",
            ],
            "articles": selection_inputs,
            "required_json_schema": {
                "selected_ids": ["article id"]
            },
        }
        result = self._json_completion(
            system_prompt=system_prompt,
            user_payload=payload,
            max_completion_tokens=_env_int("OPENAI_SELECTION_MAX_TOKENS", 800),
        )

        valid_ids = {str(item.get("id")) for item in selection_inputs}
        selected_ids = []
        for article_id in result.get("selected_ids", []):
            normalized_id = str(article_id)
            if normalized_id in valid_ids and normalized_id not in selected_ids:
                selected_ids.append(normalized_id)
            if len(selected_ids) >= max_items:
                break
        return selected_ids

    def summarize_keyword(self, keyword: str, summary_inputs: list[dict]) -> dict:
        if not summary_inputs:
            return {
                "headline": f"{keyword} 브리핑",
                "summary": "",
                "summary_status": "empty",
                "items": [],
            }

        system_prompt = (
            "You are a Korean news briefing writer for a mobile app. Write useful, "
            "substantive Korean briefings that explain the facts, context, meaning, "
            "and user-relevant implications of selected articles. Return only JSON."
        )
        payload = {
            "keyword": keyword,
            "summary_rules": [
                "Write the keyword-level summary in 5-7 complete Korean sentences.",
                "For each article, write a Korean summary in 3-4 complete sentences.",
                "Explain what happened, why it matters, and what users should pay attention to next.",
                "Use natural paragraphs, not bullet points or Markdown.",
                "Do not invent facts not present in the article content.",
                "Keep wording neutral, specific, and useful for a morning briefing.",
            ],
            "articles": summary_inputs,
            "required_json_schema": {
                "headline": "string",
                "summary": "5-7 sentence Korean keyword-level briefing",
                "items": [
                    {
                        "id": "article id",
                        "summary": "3-4 sentence Korean article-level briefing"
                    }
                ],
            },
        }
        result = self._json_completion(
            system_prompt=system_prompt,
            user_payload=payload,
            max_completion_tokens=_env_int("OPENAI_SUMMARY_MAX_TOKENS", 3000),
        )

        summaries_by_id = {}
        for item in result.get("items", []):
            summaries_by_id[str(item.get("id"))] = str(item.get("summary") or "").strip()

        return {
            "headline": str(result.get("headline") or f"{keyword} 브리핑").strip(),
            "summary": str(result.get("summary") or "").strip(),
            "summary_status": "complete",
            "items": [
                {
                    "id": article.get("id"),
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "pub_date": article.get("pub_date"),
                    "source_type": article.get("source_type"),
                    "summary": summaries_by_id.get(str(article.get("id")), ""),
                    "summary_status": "complete" if summaries_by_id.get(str(article.get("id"))) else "missing",
                }
                for article in summary_inputs
            ],
        }


class PlaceholderBriefingAI:
    """
    Temporary AI boundary.

    Stage 1 selection is deterministic for now: recent articles first, then
    longer preview. Stage 2 summaries stay blank until the real model is wired.
    """

    model_status = "not_configured"
    model = "placeholder"

    def select_article_ids(
        self,
        keyword: str,
        selection_inputs: list[dict],
        min_items: int,
        max_items: int,
    ) -> list:
        sorted_inputs = sorted(
            selection_inputs,
            key=lambda item: (_parse_pub_date(str(item.get("pub_date") or "")), len(item.get("content_preview") or "")),
            reverse=True,
        )
        limit = max(min_items, min(max_items, len(sorted_inputs)))
        return [str(item.get("id")) for item in sorted_inputs[:limit]]

    def summarize_keyword(self, keyword: str, summary_inputs: list[dict]) -> dict:
        return {
            "headline": f"{keyword} briefing",
            "summary": "",
            "summary_status": self.model_status,
            "items": [
                {
                    "id": article.get("id"),
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "pub_date": article.get("pub_date"),
                    "source_type": article.get("source_type"),
                    "summary": "",
                    "summary_status": self.model_status,
                }
                for article in summary_inputs
            ],
        }


def fetch_recent_articles_for_keyword(keyword: str, limit: int, table_name: str = "articles") -> list[dict]:
    client = get_supabase_client()
    if not client:
        return []

    try:
        res = (
            client.table(table_name)
            .select("id, keyword, title, url, content, pub_date, source_type")
            .eq("keyword", keyword)
            .order("pub_date", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as e:
        logging.warning(f"Article query failed for keyword={keyword}: {e}")
        return []

    articles = []
    for row in res.data or []:
        cleaned = _clean_article(row)
        if cleaned:
            articles.append(cleaned)
    return articles


def build_keyword_briefing(
    keyword: str,
    briefing_date: str,
    ai: Optional[BriefingAI] = None,
) -> dict:
    article_table = os.environ.get("SUPABASE_ARTICLES_TABLE", "articles").strip() or "articles"
    candidate_limit = _env_int("BRIEFING_CANDIDATE_LIMIT", 30)
    min_items = _env_int("BRIEFING_MIN_ITEMS_PER_KEYWORD", 3)
    max_items = _env_int("BRIEFING_MAX_ITEMS_PER_KEYWORD", 5)
    selection_preview_chars = _env_int("BRIEFING_SELECTION_PREVIEW_CHARS", 600)
    summary_content_chars = _env_int("BRIEFING_SUMMARY_CONTENT_CHARS", 4000)
    ai = ai or OpenAIBriefingAI()

    articles = fetch_recent_articles_for_keyword(keyword, candidate_limit, article_table)
    articles_by_id = {str(article.get("id")): article for article in articles}

    # Stage 1: cheap selection input. Real AI should only see titles + previews here.
    selection_inputs = [
        _article_for_selection(article, selection_preview_chars)
        for article in articles
    ]
    selected_ids = ai.select_article_ids(keyword, selection_inputs, min_items, max_items)
    selected = [
        articles_by_id[article_id]
        for article_id in selected_ids
        if article_id in articles_by_id
    ]

    # Stage 2: summary input only for selected articles.
    summary_inputs = [
        _article_for_summary(article, summary_content_chars)
        for article in selected
    ]
    ai_payload = ai.summarize_keyword(keyword, summary_inputs)

    return {
        "briefing_date": briefing_date,
        "keyword": keyword,
        "generated_at": datetime.now(KST).isoformat(),
        "candidate_count": len(articles),
        "selected_count": len(selected),
        "ai_model_status": ai.model_status,
        "ai_model": ai.model,
        "pipeline_strategy": "two_stage_selection_then_summary",
        "selection_input": {
            "article_count": len(selection_inputs),
            "content_preview_chars": selection_preview_chars,
            "model_status": ai.model_status,
        },
        "summary_input": {
            "article_count": len(summary_inputs),
            "content_chars_per_article": summary_content_chars,
            "model_status": ai.model_status,
        },
        **ai_payload,
    }


def generate_and_cache_briefings(briefing_date: Optional[str] = None) -> dict:
    briefing_date = briefing_date or datetime.now(KST).date().isoformat()
    keyword_table = os.environ.get("SUPABASE_USER_KEYWORDS_TABLE", "user_keywords").strip() or "user_keywords"
    ttl_seconds = _env_int("BRIEFING_REDIS_TTL_SECONDS", 172800)

    subscriptions = fetch_user_keyword_subscriptions(keyword_table)
    if not subscriptions:
        logging.warning("No user keyword subscriptions found. Briefing generation skipped.")
        return {
            "briefing_date": briefing_date,
            "subscriptions": 0,
            "keywords": 0,
            "users": 0,
            "redis_saved": 0,
        }

    keywords = []
    seen_keywords = set()
    user_keywords = {}
    for sub in subscriptions:
        user_id = sub["user_id"]
        keyword = sub["keyword"]
        user_keywords.setdefault(user_id, [])
        if keyword not in user_keywords[user_id]:
            user_keywords[user_id].append(keyword)
        if keyword not in seen_keywords:
            seen_keywords.add(keyword)
            keywords.append(keyword)

    keyword_briefings = {}
    redis_saved = 0
    for keyword in keywords:
        payload = build_keyword_briefing(keyword, briefing_date)
        keyword_briefings[keyword] = payload
        key = build_keyword_briefing_key(briefing_date, keyword)
        result = set_json(key, payload, ttl_seconds)
        if result.get("saved"):
            redis_saved += 1

    for user_id, user_keyword_list in user_keywords.items():
        payload = {
            "briefing_date": briefing_date,
            "user_id": user_id,
            "generated_at": datetime.now(KST).isoformat(),
            "ai_model_status": "configured",
            "ai_model": os.environ.get("OPENAI_BRIEFING_MODEL", "gpt-5-nano").strip() or "gpt-5-nano",
            "keywords": [
                keyword_briefings[keyword]
                for keyword in user_keyword_list
                if keyword in keyword_briefings
            ],
        }
        key = build_user_briefing_key(briefing_date, user_id)
        result = set_json(key, payload, ttl_seconds)
        if result.get("saved"):
            redis_saved += 1

    return {
        "briefing_date": briefing_date,
        "subscriptions": len(subscriptions),
        "keywords": len(keywords),
        "users": len(user_keywords),
        "redis_saved": redis_saved,
        "ttl_seconds": ttl_seconds,
    }
