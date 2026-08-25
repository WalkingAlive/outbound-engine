"""Orchestrates a single end-to-end run: gather signals -> ask the agent for a
brief -> persist it -> write a human-readable markdown digest."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from outbound_engine.agent.outbound_agent import gather_signals, generate_brief
from outbound_engine.config import OUTPUT_DIR, ensure_dirs, settings
from outbound_engine.models import DailyBrief
from outbound_engine.storage import Storage

logger = logging.getLogger(__name__)


def render_markdown(brief: DailyBrief) -> str:
    lines = [
        f"# Outbound brief for {brief.generated_for}",
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        brief.summary,
        "",
    ]
    if not brief.recommendations:
        lines.append("No recommendations today - nothing fresh enough to act on.")
    for rec in brief.recommendations:
        lines.append(f"## {rec.target_name} ({rec.priority} priority)")
        lines.append(f"**Why now:** {rec.reasoning}")
        lines.append(f"**Action:** {rec.recommended_action}")
        lines.append(f"**Signals:** {', '.join(rec.signal_ids) or 'n/a'}")
        lines.append("")
        lines.append(f"**Draft ({rec.draft.channel}):**")
        if rec.draft.subject:
            lines.append(f"> Subject: {rec.draft.subject}")
        for line in rec.draft.body.splitlines():
            lines.append(f"> {line}")
        lines.append("")
    return "\n".join(lines)


def run_daily_digest(
    repo_paths: list[str] | None = None,
    linkedin_export_paths: dict[str, str] | None = None,
    write_markdown: bool = True,
) -> DailyBrief:
    ensure_dirs()
    store = Storage()
    targets = store.list_targets()
    if not targets:
        logger.warning("No targets configured - add one with `outbound-engine add-target`.")

    repo_paths = repo_paths if repo_paths is not None else store.list_repos()

    signals = gather_signals(
        targets, repo_paths=repo_paths, linkedin_export_paths=linkedin_export_paths
    )
    new_signals = store.save_signals(signals)
    logger.info("Gathered %d signals (%d new)", len(signals), len(new_signals))

    # Always brief on the full unsurfaced backlog, not just this run's fetch,
    # so nothing gets lost if a run is interrupted before the brief is written.
    unsurfaced = store.unsurfaced_signals()
    brief = generate_brief(unsurfaced, targets)

    store.save_brief(brief)
    surfaced_ids = {sid for rec in brief.recommendations for sid in rec.signal_ids}
    store.mark_surfaced(list(surfaced_ids))

    if write_markdown:
        out_path = Path(OUTPUT_DIR) / f"brief-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')}.md"
        out_path.write_text(render_markdown(brief))
        logger.info("Wrote %s", out_path)

    return brief
