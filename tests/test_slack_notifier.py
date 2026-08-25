import dataclasses

from outbound_engine.models import DailyBrief, DraftMessage, Recommendation
from outbound_engine.notifiers.slack import brief_to_blocks, is_configured


def _brief(recs=None):
    return DailyBrief(generated_for="you", summary="Two solid openings today.", recommendations=recs or [])


def test_brief_to_blocks_empty():
    blocks = brief_to_blocks(_brief())
    assert blocks[0]["type"] == "header"
    assert any("No recommendations" in b.get("text", {}).get("text", "") for b in blocks if b["type"] == "section")


def test_brief_to_blocks_with_recommendation():
    rec = Recommendation(
        target_name="Jane Doe",
        target_type="person",
        priority="high",
        reasoning="She just raised a seed round.",
        signal_ids=["abc123"],
        recommended_action="Send a congrats note referencing the raise.",
        draft=DraftMessage(channel="linkedin", body="Congrats on the raise, Jane!"),
    )
    blocks = brief_to_blocks(_brief([rec]))
    text_blocks = [b["text"]["text"] for b in blocks if b["type"] == "section"]
    assert any("Jane Doe" in t for t in text_blocks)
    assert any("Congrats on the raise" in t for t in text_blocks)
    # dividers separate each recommendation
    assert any(b["type"] == "divider" for b in blocks)


def test_is_configured_requires_both_token_and_user(monkeypatch):
    import outbound_engine.notifiers.slack as slack_notifier

    # `settings` is a frozen dataclass instance - rebind the module-level name
    # to a modified copy rather than mutating it in place.
    unconfigured = dataclasses.replace(
        slack_notifier.settings, slack_bot_token=None, slack_allowed_user_id="U123"
    )
    monkeypatch.setattr(slack_notifier, "settings", unconfigured)
    assert is_configured() is False

    configured = dataclasses.replace(unconfigured, slack_bot_token="xoxb-fake")
    monkeypatch.setattr(slack_notifier, "settings", configured)
    assert is_configured() is True
