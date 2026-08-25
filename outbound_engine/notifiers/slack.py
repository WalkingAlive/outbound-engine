"""Delivers a DailyBrief straight to your Slack DM - never a channel.

Used two ways:
- One-way push: `run`/`watch` call post_brief() after generating a brief, if
  SLACK_BOT_TOKEN + SLACK_ALLOWED_USER_ID are set. No bot process needs to
  be running for this - it's a single API call.
- From the interactive bot (slack_app.py), which also uses brief_to_blocks()
  to render the brief it just generated on demand.
"""

from __future__ import annotations

import logging

from outbound_engine.config import settings
from outbound_engine.models import DailyBrief, Recommendation

logger = logging.getLogger(__name__)

_SECTION_TEXT_LIMIT = 2900  # Slack's hard cap is 3000 chars per section text block


def _truncate(text: str, limit: int = _SECTION_TEXT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n_(truncated)_"


def _recommendation_blocks(rec: Recommendation) -> list[dict]:
    header = (
        f"*{rec.target_name}* — {rec.priority} priority\n"
        f"*Why now:* {rec.reasoning}\n"
        f"*Action:* {rec.recommended_action}"
    )
    draft_label = f"Draft ({rec.draft.channel})"
    if rec.draft.subject:
        draft_label += f" — _{rec.draft.subject}_"
    quoted_body = "\n".join(f">{line}" for line in rec.draft.body.splitlines()) or ">"
    return [
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": _truncate(header)}},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": _truncate(f"*{draft_label}:*\n{quoted_body}")},
        },
    ]


def brief_to_blocks(brief: DailyBrief) -> list[dict]:
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Outbound brief for {brief.generated_for}"},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": _truncate(brief.summary)}},
    ]
    if not brief.recommendations:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No recommendations today - nothing fresh enough to act on._"},
            }
        )
    for rec in brief.recommendations:
        blocks.extend(_recommendation_blocks(rec))
    return blocks


def is_configured() -> bool:
    return bool(settings.slack_bot_token and settings.slack_allowed_user_id)


def post_brief(brief: DailyBrief) -> bool:
    """Post the brief to SLACK_ALLOWED_USER_ID's DM.

    Returns True if it was posted, False if Slack isn't configured (not an
    error - Slack delivery is optional). Raises on an actual Slack API
    failure so callers can decide whether that should be fatal.
    """
    if not is_configured():
        return False

    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=settings.slack_bot_token)
    try:
        opened = client.conversations_open(users=[settings.slack_allowed_user_id])
        channel_id = opened["channel"]["id"]
        client.chat_postMessage(
            channel=channel_id,
            text=f"Outbound brief for {brief.generated_for}: {brief.summary}",
            blocks=brief_to_blocks(brief),
        )
    except SlackApiError:
        logger.exception("Failed to post brief to Slack")
        raise
    return True
