"""Generic web page fetching, for pulling context from a URL the agent was pointed at
(e.g. a company blog post, a press release, a personal site).

Respects robots.txt and identifies itself with a real User-Agent. This is a
plain single-page fetch+extract, not a crawler - it never follows links on
its own and makes one request per call.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from outbound_engine.config import settings
from outbound_engine.models import Signal

logger = logging.getLogger(__name__)

USER_AGENT = "OutboundEngineBot/0.1 (+https://github.com/; respects robots.txt)"


def _allowed_by_robots(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        # If robots.txt is unreachable, don't block on it - but don't ignore
        # a hard disallow either; this only covers the "can't verify" case.
        return True
    return rp.can_fetch(USER_AGENT, url)


def fetch_page(url: str, target: str) -> Signal | None:
    """Fetch a single URL and return it as a Signal with readable text extracted."""
    if not _allowed_by_robots(url):
        logger.info("Skipping %s: disallowed by robots.txt", url)
        return None

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=settings.web_request_timeout,
        )
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to fetch %s", url)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else url
    text = " ".join(soup.get_text(separator=" ").split())

    return Signal(
        source="web",
        target=target,
        title=title,
        body=text[:4000],
        url=url,
    )
