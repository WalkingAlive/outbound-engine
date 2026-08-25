"""'What I'm working on' context, so drafts can reference the sender's real work
instead of generic pitches.

Local git history is the one source this ships with a real implementation for
(no third-party auth needed). Slack/Notion/Calendar are common next sources -
`WorkContextSource` documents the interface so they drop in the same way.
"""

from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

from outbound_engine.config import settings
from outbound_engine.models import Signal

logger = logging.getLogger(__name__)


class WorkContextSource(ABC):
    """A source of 'what the user is working on' context, surfaced as Signals
    with source='workspace'. Implement this for Slack, Notion, a calendar, etc.
    """

    @abstractmethod
    def recent_activity(self, days: int) -> list[Signal]: ...


def recent_git_activity(
    repo_paths: list[str], days: int = settings.workspace_git_days
) -> list[Signal]:
    """Summarize recent commits across the given local git repos."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    signals = []
    for repo in repo_paths:
        repo_path = Path(repo)
        if not (repo_path / ".git").exists():
            logger.warning("Not a git repo, skipping: %s", repo)
            continue
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--since={since}",
                    "--pretty=format:%h|%ad|%s",
                    "--date=short",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
        except (subprocess.SubprocessError, OSError):
            logger.exception("git log failed for %s", repo_path)
            continue

        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            continue

        commit_summaries = []
        for line in lines[:25]:
            parts = line.split("|", 2)
            if len(parts) == 3:
                commit_summaries.append(f"{parts[1]}: {parts[2]}")

        signals.append(
            Signal(
                source="workspace",
                target="__self__",
                title=f"Recent work on {repo_path.name}",
                body="\n".join(commit_summaries)[:3000],
                url=None,
                published_at=datetime.now(timezone.utc).isoformat(),
            )
        )
    return signals
