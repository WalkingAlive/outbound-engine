"""News gathering via Google News RSS.

RSS is a public syndication format meant to be polled - no API key, no ToS
issue, no scraping. This is the primary "what's happening with this person /
company" signal source.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import feedparser

from outbound_engine.models import Signal

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def fetch_news(target: str, query: str | None = None, limit: int = 5) -> list[Signal]:
    """Fetch recent news mentioning `query` (defaults to the target's name).

    Args:
        target: the tracked entity name these signals are attributed to.
        query: search string, e.g. '"Jane Doe" AND Acme Corp'. Defaults to `target`.
        limit: max number of items to return.
    """
    q = query or target
    url = GOOGLE_NEWS_RSS.format(query=quote_plus(q))
    try:
        parsed = feedparser.parse(url)
    except Exception:
        logger.exception("Failed to fetch/parse news feed for %r", q)
        return []

    if getattr(parsed, "bozo", False) and not parsed.entries:
        logger.warning("News feed for %r returned no usable entries", q)
        return []

    signals = []
    for entry in parsed.entries[:limit]:
        title = entry.get("title", "").strip()
        if not title:
            continue
        source_name = ""
        if "source" in entry and isinstance(entry["source"], dict):
            source_name = entry["source"].get("title", "")
        summary = entry.get("summary", "")
        body = f"{source_name}: {summary}" if source_name else summary
        signals.append(
            Signal(
                source="news",
                target=target,
                title=title,
                body=body[:2000],
                url=entry.get("link"),
                published_at=entry.get("published"),
            )
        )
    return signals
