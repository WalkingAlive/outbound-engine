"""LinkedIn signal ingestion.

LinkedIn's Terms of Service prohibit automated scraping of the site, and its
official API does not offer general-purpose "monitor any profile's activity"
access (that surface is restricted to specific partner programs). So this
connector deliberately does NOT log in to linkedin.com or drive a browser
against it. Instead it supports two ToS-compliant paths:

1. `ingest_export()` - turn data you already lawfully have (a manual export,
   a paste of post text you copied yourself, or output from a compliant
   browser extension you use interactively) into Signals.
2. `LinkedInProvider` - a small interface you can implement against a
   compliant third-party data provider you have a contract with (e.g. a
   licensed people-data API). Point `LINKEDIN_PROVIDER_MODULE` at your
   implementation and it's picked up automatically; none is bundled here
   since the right provider depends on your contract and your ToS review.
"""

from __future__ import annotations

import importlib
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from outbound_engine.config import settings
from outbound_engine.models import Signal

logger = logging.getLogger(__name__)


def ingest_export(target: str, path: str | Path) -> list[Signal]:
    """Load posts/updates from a local JSON or CSV file you exported or pasted yourself.

    Expected JSON shape: a list of objects with at least a "text" field and
    optionally "url" and "published_at". CSV: columns text,url,published_at.
    """
    path = Path(path)
    if not path.exists():
        logger.warning("LinkedIn export not found: %s", path)
        return []

    items: list[dict]
    if path.suffix.lower() == ".json":
        items = json.loads(path.read_text())
    elif path.suffix.lower() == ".csv":
        import csv

        with path.open(newline="") as f:
            items = list(csv.DictReader(f))
    else:
        logger.warning("Unsupported LinkedIn export format: %s", path.suffix)
        return []

    signals = []
    for item in items:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        signals.append(
            Signal(
                source="linkedin",
                target=target,
                title=text[:80] + ("..." if len(text) > 80 else ""),
                body=text[:2000],
                url=item.get("url"),
                published_at=item.get("published_at"),
            )
        )
    return signals


class LinkedInProvider(ABC):
    """Implement this against a compliant, licensed LinkedIn data provider.

    This project does not bundle a concrete implementation - choose a
    provider whose terms actually permit this use case and who you have a
    commercial relationship with, then wire it in via
    LINKEDIN_PROVIDER_MODULE=your_package.your_module:YourProviderClass
    """

    @abstractmethod
    def recent_activity(self, handle: str, limit: int = 5) -> list[dict]:
        """Return recent posts/updates as dicts with text/url/published_at keys."""


def get_configured_provider() -> LinkedInProvider | None:
    if not settings.linkedin_provider_module:
        return None
    module_path, _, class_name = settings.linkedin_provider_module.partition(":")
    if not class_name:
        logger.error(
            "LINKEDIN_PROVIDER_MODULE must be 'package.module:ClassName', got %r",
            settings.linkedin_provider_module,
        )
        return None
    try:
        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)
        return provider_cls()
    except Exception:
        logger.exception("Failed to load LinkedIn provider %s", settings.linkedin_provider_module)
        return None


def fetch_via_provider(target: str, handle: str, limit: int = 5) -> list[Signal]:
    provider = get_configured_provider()
    if provider is None:
        return []
    try:
        items = provider.recent_activity(handle, limit=limit)
    except Exception:
        logger.exception("LinkedIn provider lookup failed for %s", handle)
        return []

    signals = []
    for item in items[:limit]:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        signals.append(
            Signal(
                source="linkedin",
                target=target,
                title=text[:80] + ("..." if len(text) > 80 else ""),
                body=text[:2000],
                url=item.get("url"),
                published_at=item.get("published_at"),
            )
        )
    return signals
