"""
Redis helpers for temporary briefing storage.
"""

import json
import logging
import os
from typing import Optional
from urllib.parse import quote, urlparse, urlunparse

try:
    import redis
except ImportError:
    redis = None

_REDIS_CLIENT = None
_REDIS_CHECKED = False


def _load_env_if_exists() -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip("'").strip('"')
    except Exception as e:
        logging.warning(f".env load warning: {e}")


def get_redis_client():
    global _REDIS_CLIENT, _REDIS_CHECKED

    if _REDIS_CHECKED:
        return _REDIS_CLIENT

    _REDIS_CHECKED = True
    _load_env_if_exists()

    if redis is None:
        logging.warning("redis package is not installed. Run: pip install redis")
        return None

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0").strip()
    parsed = urlparse(redis_url)
    if parsed.scheme == "redis" and parsed.hostname and parsed.hostname.endswith(".upstash.io"):
        redis_url = urlunparse(parsed._replace(scheme="rediss"))

    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        _REDIS_CLIENT = client
        return _REDIS_CLIENT
    except Exception as e:
        logging.warning(f"Redis connection failed: {e}")
        return None


def set_json(key: str, value: dict, ttl_seconds: int) -> dict:
    client = get_redis_client()
    if not client:
        return {"enabled": False, "saved": False, "key": key}

    payload = json.dumps(value, ensure_ascii=False)
    client.setex(key, ttl_seconds, payload)
    return {"enabled": True, "saved": True, "key": key, "ttl_seconds": ttl_seconds}


def get_json(key: str) -> Optional[dict]:
    client = get_redis_client()
    if not client:
        return None

    raw = client.get(key)
    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logging.warning(f"Redis value is not valid JSON: {key}")
        return None


def build_keyword_briefing_key(briefing_date: str, keyword: str) -> str:
    encoded_keyword = quote(keyword, safe="")
    return f"briefing:{briefing_date}:keyword:{encoded_keyword}"


def build_user_briefing_key(briefing_date: str, user_id: str) -> str:
    return f"briefing:{briefing_date}:user:{user_id}"
