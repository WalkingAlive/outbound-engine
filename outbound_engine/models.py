"""Core data types shared across connectors, storage, and the agent."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

SignalSource = Literal["news", "x", "linkedin", "web", "workspace"]
TargetType = Literal["person", "company"]


@dataclass
class Signal:
    """A single observed data point about a tracked target (a news hit, a post, a commit, ...)."""

    source: SignalSource
    target: str
    title: str
    body: str
    url: Optional[str] = None
    published_at: Optional[str] = None
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = self.dedup_hash()

    def dedup_hash(self) -> str:
        """Stable id used to avoid re-surfacing the same signal on every run."""
        basis = self.url or f"{self.source}:{self.target}:{self.title}"
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


@dataclass
class Target:
    """An entity (person or company) the agent watches for outbound opportunities."""

    name: str
    type: TargetType
    keywords: list[str] = field(default_factory=list)
    linkedin_handle: Optional[str] = None
    x_handle: Optional[str] = None
    notes: Optional[str] = None


# --- Structured LLM output -------------------------------------------------
# These feed `client.messages.parse(..., output_format=DailyBrief)`.


class DraftMessage(BaseModel):
    channel: Literal["email", "linkedin", "x_dm", "call_note"] = Field(
        description="Where this draft is meant to be sent."
    )
    subject: Optional[str] = Field(
        default=None, description="Subject line, only for email."
    )
    body: str = Field(description="The full draft message, ready to review and send.")


class Recommendation(BaseModel):
    target_name: str
    target_type: TargetType
    priority: Literal["high", "medium", "low"]
    reasoning: str = Field(
        description="Why this outreach makes sense right now, grounded in the cited signals."
    )
    signal_ids: list[str] = Field(
        description="IDs of the signals (from the provided context) that justify this recommendation."
    )
    recommended_action: str = Field(
        description="The concrete next step, e.g. 'Reply to their LinkedIn post about X' or 'Send intro email referencing Y'."
    )
    draft: DraftMessage


class DailyBrief(BaseModel):
    generated_for: str
    summary: str = Field(description="2-3 sentence overview of today's outbound picture.")
    recommendations: list[Recommendation]
