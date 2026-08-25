"""The outbound-specialist agent: turns tracked targets into signals, then
signals into a DailyBrief of recommendations and drafts.

Two phases, both backed by Claude:
1. gather_signals() - deterministic, code-driven fan-out across connectors.
   No LLM call; this is plain data collection so it's cheap to run often.
2. generate_brief() - LLM-driven. First an exploratory tool-use pass (the
   agent can pull extra context via the read_url tool), then a structured
   `messages.parse()` call that produces the typed DailyBrief.
"""

from __future__ import annotations

import logging

import anthropic

from outbound_engine.agent.prompts import render_system_prompt
from outbound_engine.agent.tools import read_url
from outbound_engine.config import settings
from outbound_engine.connectors import linkedin, news, workspace, x_twitter
from outbound_engine.models import DailyBrief, Signal, Target

logger = logging.getLogger(__name__)


def gather_signals(
    targets: list[Target],
    repo_paths: list[str] | None = None,
    linkedin_export_paths: dict[str, str] | None = None,
) -> list[Signal]:
    """Deterministically pull fresh signals for every tracked target plus
    workspace context. Safe to call frequently - connectors are read-only."""
    signals: list[Signal] = []

    if repo_paths:
        signals.extend(workspace.recent_git_activity(repo_paths))

    linkedin_export_paths = linkedin_export_paths or {}

    for target in targets:
        query = f'"{target.name}"'
        if target.keywords:
            query += " " + " ".join(target.keywords)
        signals.extend(
            news.fetch_news(target.name, query=query, limit=settings.news_results_per_target)
        )

        if target.x_handle:
            signals.extend(x_twitter.get_user_recent_posts(target.name, target.x_handle))

        if target.name in linkedin_export_paths:
            signals.extend(
                linkedin.ingest_export(target.name, linkedin_export_paths[target.name])
            )
        elif target.linkedin_handle:
            signals.extend(
                linkedin.fetch_via_provider(target.name, target.linkedin_handle)
            )

    return signals


def _format_signals_block(signals: list[Signal]) -> str:
    lines = []
    for s in signals:
        lines.append(
            f"- id={s.id} source={s.source} target={s.target!r} "
            f"published={s.published_at or 'unknown'}\n"
            f"  title: {s.title}\n"
            f"  body: {s.body[:600]}\n"
            f"  url: {s.url or 'n/a'}"
        )
    return "\n".join(lines) if lines else "(no signals)"


def generate_brief(
    signals: list[Signal],
    targets: list[Target],
    user_name: str | None = None,
    client: anthropic.Anthropic | None = None,
    model: str | None = None,
    allow_url_lookups: bool = True,
) -> DailyBrief:
    """Run the outbound specialist over the gathered signals and return a
    structured DailyBrief with prioritized recommendations and drafts."""
    client = client or anthropic.Anthropic()
    model = model or settings.claude_model
    user_name = user_name or settings.user_name
    system_prompt = render_system_prompt(user_name)

    target_lines = "\n".join(
        f"- {t.name} ({t.type}){': ' + t.notes if t.notes else ''}" for t in targets
    )
    signals_block = _format_signals_block(signals)
    workspace_block = _format_signals_block(
        [s for s in signals if s.source == "workspace"]
    )
    external_signals = [s for s in signals if s.source != "workspace"]
    external_block = _format_signals_block(external_signals)

    research_prompt = f"""\
Tracked targets:
{target_lines or '(none)'}

What {user_name} is currently working on (workspace signals):
{workspace_block}

External signals gathered this run:
{external_block}

Review the signals above. If a URL looks worth reading in full before you \
judge whether it justifies outreach, use the read_url tool. When you're \
done researching, write a short plain-text summary of which targets \
deserve a recommendation and why - you'll be asked to formalize it next.
"""

    tools = [read_url] if allow_url_lookups else []

    transcript_summary = research_prompt
    if tools:
        runner = client.beta.messages.tool_runner(
            model=model,
            max_tokens=8000,
            system=system_prompt,
            tools=tools,
            messages=[{"role": "user", "content": research_prompt}],
        )
        last_text = None
        for message in runner:
            texts = [b.text for b in message.content if b.type == "text"]
            if texts:
                last_text = "\n".join(texts)
        if last_text:
            transcript_summary = f"{research_prompt}\n\nYour research notes:\n{last_text}"

    parse_response = client.messages.parse(
        model=model,
        max_tokens=8000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{transcript_summary}\n\n"
                    f"Now produce the final DailyBrief for {user_name}. Only include "
                    "targets that genuinely earn a recommendation this run - it's fine "
                    "for the list to be shorter than the tracked-targets list."
                ),
            }
        ],
        output_format=DailyBrief,
    )
    return parse_response.parsed_output
