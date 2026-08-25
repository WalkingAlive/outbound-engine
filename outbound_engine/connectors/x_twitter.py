"""X (Twitter) monitoring via the official X API v2.

Requires a developer app + bearer token (X_BEARER_TOKEN). This intentionally
uses the documented REST API rather than scraping the site, which X's ToS
prohibits and which is also unreliable (auth walls, bot detection).

Docs: https://developer.x.com/en/docs/x-api
"""

from __future__ import annotations

import logging

import requests

from outbound_engine.config import settings
from outbound_engine.models import Signal

logger = logging.getLogger(__name__)

API_BASE = "https://api.x.com/2"


class XNotConfigured(RuntimeError):
    """Raised when X_BEARER_TOKEN isn't set. Callers should treat this as 'skip, not fatal'."""


def _headers() -> dict[str, str]:
    if not settings.x_bearer_token:
        raise XNotConfigured("X_BEARER_TOKEN is not set; skipping X monitoring.")
    return {"Authorization": f"Bearer {settings.x_bearer_token}"}


def _get(path: str, params: dict) -> dict:
    resp = requests.get(
        f"{API_BASE}{path}",
        headers=_headers(),
        params=params,
        timeout=settings.web_request_timeout,
    )
    resp.raise_for_status()
    return resp.json()


def get_user_recent_posts(target: str, handle: str, limit: int = 5) -> list[Signal]:
    """Fetch a tracked profile's recent original posts (official API, requires the
    account be public and your app to have the appropriate access level)."""
    handle = handle.lstrip("@")
    try:
        user = _get(f"/users/by/username/{handle}", {})
    except XNotConfigured as e:
        logger.info(str(e))
        return []
    except requests.RequestException:
        logger.exception("Failed to resolve X user %s", handle)
        return []

    user_id = user.get("data", {}).get("id")
    if not user_id:
        logger.warning("No such X user: %s", handle)
        return []

    try:
        timeline = _get(
            f"/users/{user_id}/tweets",
            {
                "max_results": max(5, min(limit, 100)),
                "tweet.fields": "created_at,public_metrics",
                "exclude": "retweets,replies",
            },
        )
    except requests.RequestException:
        logger.exception("Failed to fetch timeline for %s", handle)
        return []

    signals = []
    for tweet in timeline.get("data", [])[:limit]:
        signals.append(
            Signal(
                source="x",
                target=target,
                title=f"@{handle} posted",
                body=tweet.get("text", "")[:2000],
                url=f"https://x.com/{handle}/status/{tweet['id']}",
                published_at=tweet.get("created_at"),
            )
        )
    return signals


def search_recent(target: str, query: str, limit: int = 5) -> list[Signal]:
    """Search recent public posts matching a query (last 7 days, standard search endpoint)."""
    try:
        result = _get(
            "/tweets/search/recent",
            {
                "query": query,
                "max_results": max(10, min(limit, 100)),
                "tweet.fields": "created_at,author_id",
            },
        )
    except XNotConfigured as e:
        logger.info(str(e))
        return []
    except requests.RequestException:
        logger.exception("X recent search failed for query %r", query)
        return []

    signals = []
    for tweet in result.get("data", [])[:limit]:
        signals.append(
            Signal(
                source="x",
                target=target,
                title=f"Mention matching '{query}'",
                body=tweet.get("text", "")[:2000],
                url=f"https://x.com/i/web/status/{tweet['id']}",
                published_at=tweet.get("created_at"),
            )
        )
    return signals
