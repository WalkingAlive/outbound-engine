"""Tools exposed to the outbound-specialist agent during the research phase.

Kept intentionally small: the agent's job here is judgment, not fetching, so
most signal gathering already happened deterministically (see
outbound_agent.gather_signals). The one tool given to the model lets it
pull additional context from a specific URL it was handed (e.g. read the
full article behind a news headline) before it writes recommendations.
"""

from __future__ import annotations

from anthropic import beta_tool

from outbound_engine.connectors.web import fetch_page


@beta_tool
def read_url(url: str) -> str:
    """Fetch a web page's readable text content. Use this to get more detail on a
    URL you were given (a news link, a post link, a company page) before deciding
    whether it justifies an outbound recommendation.

    Args:
        url: The full URL to fetch, e.g. "https://example.com/article".
    """
    signal = fetch_page(url, target="__lookup__")
    if signal is None:
        return f"Could not fetch {url} (blocked by robots.txt, or the request failed)."
    return f"{signal.title}\n\n{signal.body}"
