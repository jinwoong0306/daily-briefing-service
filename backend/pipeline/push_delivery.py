"""
Deliver cached user briefings through an app-push boundary.

The real push provider is not wired yet. PlaceholderPushProvider keeps the
delivery flow testable without sending production notifications.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import pytz

from redis_cache import build_user_briefing_key, get_json
from supabase_uploader import (
    fetch_user_keyword_subscriptions,
    get_supabase_client,
)


KST = pytz.timezone("Asia/Seoul")


def fetch_push_tokens(table_name: str = "user_push_tokens") -> list[dict]:
    client = get_supabase_client()
    if not client:
        return []

    try:
        res = (
            client.table(table_name)
            .select("user_id, platform, token, enabled")
            .eq("enabled", True)
            .execute()
        )
    except Exception as e:
        logging.warning(f"Push token query failed: {e}")
        return []

    tokens = []
    seen = set()
    for row in res.data or []:
        user_id = str(row.get("user_id") or "").strip()
        token = str(row.get("token") or "").strip()
        platform = str(row.get("platform") or "").strip()
        if not user_id or not token:
            continue
        key = (user_id, token)
        if key in seen:
            continue
        seen.add(key)
        tokens.append({"user_id": user_id, "platform": platform, "token": token})
    return tokens


class PlaceholderPushProvider:
    provider_name = "placeholder"

    def send(self, token: dict, title: str, body: str, data: dict) -> dict:
        logging.info(
            "Push provider is not configured. "
            f"Dry-run for user_id={token.get('user_id')} platform={token.get('platform')}"
        )
        return {
            "provider": self.provider_name,
            "sent": False,
            "dry_run": True,
            "reason": "push_provider_not_configured",
        }


def _briefing_push_copy(briefing: dict) -> tuple[str, str]:
    keyword_count = len(briefing.get("keywords", []))
    title = os.environ.get("PUSH_TITLE", "오늘의 맞춤 뉴스 브리핑")
    body = os.environ.get("PUSH_BODY", f"{keyword_count}개 관심 키워드의 새 브리핑이 도착했습니다.")
    return title, body


def deliver_cached_briefings(briefing_date: Optional[str] = None) -> dict:
    briefing_date = briefing_date or datetime.now(KST).date().isoformat()
    keyword_table = os.environ.get("SUPABASE_USER_KEYWORDS_TABLE", "user_keywords").strip() or "user_keywords"
    push_token_table = os.environ.get("SUPABASE_PUSH_TOKENS_TABLE", "user_push_tokens").strip() or "user_push_tokens"

    subscriptions = fetch_user_keyword_subscriptions(keyword_table)
    user_ids = []
    seen_users = set()
    for sub in subscriptions:
        user_id = sub["user_id"]
        if user_id in seen_users:
            continue
        seen_users.add(user_id)
        user_ids.append(user_id)

    tokens = fetch_push_tokens(push_token_table)
    tokens_by_user = {}
    for token in tokens:
        tokens_by_user.setdefault(token["user_id"], []).append(token)

    provider = PlaceholderPushProvider()
    attempted = 0
    sent = 0
    missing_briefings = 0
    users_without_tokens = 0

    for user_id in user_ids:
        briefing = get_json(build_user_briefing_key(briefing_date, user_id))
        if not briefing:
            missing_briefings += 1
            continue

        user_tokens = tokens_by_user.get(user_id, [])
        if not user_tokens:
            users_without_tokens += 1
            continue

        title, body = _briefing_push_copy(briefing)
        data = {
            "type": "briefing",
            "briefing_date": briefing_date,
            "redis_key": build_user_briefing_key(briefing_date, user_id),
        }
        for token in user_tokens:
            attempted += 1
            result = provider.send(token, title, body, data)
            if result.get("sent"):
                sent += 1

    return {
        "briefing_date": briefing_date,
        "users": len(user_ids),
        "push_tokens": len(tokens),
        "attempted": attempted,
        "sent": sent,
        "missing_briefings": missing_briefings,
        "users_without_tokens": users_without_tokens,
        "provider": provider.provider_name,
    }
