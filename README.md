# outbound-engine

A proactive recommendation-and-writing agent for outbound sales. It watches
news, X (Twitter), and (optionally) LinkedIn for signals about the people and
companies you're tracking, cross-references them with what you're actually
working on, and hands you a prioritized daily brief with ready-to-send draft
messages — grounded in real, cited signals, never generic mail-merge copy.

## How it works

```
targets (people/companies you track)
        │
        ▼
 connectors/  ──►  news (Google News RSS)
                    x_twitter (official X API v2)
                    linkedin (manual export, or your own compliant provider)
                    web (single-page fetch, robots.txt-respecting)
                    workspace (local git activity = "what I'm working on")
        │
        ▼
   storage.py (SQLite: targets, seen signals, brief history — dedupes so
               the same news item never surfaces twice)
        │
        ▼
 agent/outbound_agent.py  ──►  Claude (the "outbound specialist")
   1. exploratory pass: agent can pull extra context via a read_url tool
   2. structured pass: client.messages.parse() → a typed DailyBrief
        │
        ▼
  digest.py → output/brief-*.md  +  saved in SQLite
        │
        ▼
  notifiers/slack.py → your Slack DM (optional; never a channel)
```

The "fine-tuning" is a carefully written system prompt
(`agent/prompts.py`), not a literally fine-tuned model — that's a deliberate
choice: the persona, judgment calls, and house style live in an editable,
version-controlled prompt instead of a training run, which is far cheaper to
iterate on for a task like this. If you outgrow it, `agent/outbound_agent.py`
is the only place that would need to change to point at a fine-tuned model
ID.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY and OUTBOUND_ENGINE_USER_NAME
```

Everything else in `.env` is optional and each connector degrades gracefully
if unconfigured (news always works with no key; X and LinkedIn just get
skipped for a target until you wire them up).

## Usage

```bash
# Track targets
python -m outbound_engine.cli add-target --name "Jane Doe" --type person \
  --x-handle janedoe --keywords "raised seed" "hiring GTM" \
  --notes "Warm intro via Alex; evaluating outbound tooling"

python -m outbound_engine.cli add-target --name "Acme Corp" --type company

# Point it at your own repos so drafts can reference real current work
python -m outbound_engine.cli add-repo ~/code/my-product

# One-off run → writes output/brief-<timestamp>.md
python -m outbound_engine.cli run

# Or run continuously (long-lived process, e.g. in a container)
python -m outbound_engine.cli watch --interval-hours 24
```

For most deployments, prefer a cron job / systemd timer calling
`python -m outbound_engine.cli run` over `watch` — simpler, no long-lived
process to babysit:

```cron
0 8 * * * cd /path/to/outbound-engine && .venv/bin/python -m outbound_engine.cli run
```

## Slack

There are two independent pieces — use either or both:

- **Brief delivery to your DM** — `run`/`watch` push the finished brief
  straight to your Slack DM (in addition to the markdown file) whenever
  `SLACK_BOT_TOKEN` + `SLACK_ALLOWED_USER_ID` are set. No bot process needs
  to be running for this; a cron job calling `run` is enough.
- **Two-way chat** — `python -m outbound_engine.cli slack` starts a bot that
  you DM directly. Send it the same commands as the CLI and it replies in
  the thread:

  ```
  add-target --name "Jane Doe" --type person --x-handle janedoe --keywords "seed round" "hiring"
  list-targets
  run
  ```

  `run` triggers a live gather-and-brief cycle and posts the result back
  into the DM as formatted blocks. Add `--interval-hours 24` to also push a
  brief proactively on a cadence from the same process, so one running
  process covers both "ping me daily" and "let me ask on demand."

Everything only ever happens in your **direct message** with the bot — it
never posts to a channel, and it ignores DMs from anyone but
`SLACK_ALLOWED_USER_ID`. This bot spends your Anthropic/X API quota and can
add tracked targets, so treat it like it has your credentials (because it
does) — don't skip setting `SLACK_ALLOWED_USER_ID`.

### Slack setup

1. Go to <https://api.slack.com/apps> → **Create New App** → **From scratch**.
   Name it (e.g. "Outbound Engine"), pick your workspace.
2. **Socket Mode** (left sidebar) → toggle it on. When prompted, generate an
   app-level token with the `connections:write` scope → this is
   `SLACK_APP_TOKEN` (starts with `xapp-`).
3. **OAuth & Permissions** → under **Bot Token Scopes**, add:
   `chat:write`, `im:write`, `im:history`, `users:read`.
   Click **Install to Workspace** at the top of that page → copy the
   **Bot User OAuth Token** → this is `SLACK_BOT_TOKEN` (starts with `xoxb-`).
4. **Event Subscriptions** → toggle on → under **Subscribe to bot events**,
   add `message.im`. Save.
5. Find your own Slack user ID: in Slack, click your profile picture → **…**
   → **Copy member ID**. This is `SLACK_ALLOWED_USER_ID` (looks like `U0123ABC456`).
6. Put all three in `.env`, then DM the app's bot user in Slack (find it
   under **Apps** in your sidebar, or search its name) — send `help` to
   confirm it responds — and run:

   ```bash
   python -m outbound_engine.cli slack --interval-hours 24
   ```

Keep this process running wherever you'd run any long-lived bot (your
machine, a small VM, a container) — Socket Mode means it just needs
outbound internet, no public URL or inbound port.

## Connectors

| Connector | Needs | Notes |
|---|---|---|
| `news` | nothing | Google News RSS search per target. No API key. |
| `x_twitter` | `X_BEARER_TOKEN` | Official X API v2 (`api.x.com`) — user timeline + recent search. |
| `linkedin` | nothing, for manual ingest | `ingest_export()` reads a JSON/CSV you exported or pasted yourself. See below. |
| `linkedin` (provider) | `LINKEDIN_PROVIDER_MODULE` | Adapter interface for a *compliant, licensed* third-party LinkedIn data provider you have a contract with. |
| `web` | nothing | Single-page fetch + text extraction, checks `robots.txt` first. |
| `workspace` | nothing | `git log` across repos you register with `add-repo`, as "what I'm working on" context. |

### Why no LinkedIn scraper

LinkedIn's Terms of Service prohibit automated scraping, and its public API
doesn't offer general "watch any profile's activity" access — that's
restricted to specific partner programs. Rather than build something that
logs into linkedin.com or drives a headless browser to get around that (which
would also just get your account banned), this project supports two
compliant paths instead:

1. **Manual export/paste** (`linkedin.ingest_export`) — for posts you already
   have lawful access to (something you copied yourself, or exported via a
   tool you use interactively).
2. **Bring your own licensed provider** — implement
   `outbound_engine.connectors.linkedin.LinkedInProvider` against a data
   provider you have a commercial agreement with, and point
   `LINKEDIN_PROVIDER_MODULE` at it.

### Adding a new connector

Any function that returns `list[outbound_engine.models.Signal]` works. Wire
it into `agent.outbound_agent.gather_signals()`. Good next candidates: Slack
*as a signal source* (mentions of a target in your own workspace — separate
from the Slack DM delivery/chat interface above), a calendar (upcoming
meetings with a target), Notion/CRM (deal stage, notes).

## Data & privacy

- All state lives locally in SQLite (`OUTBOUND_ENGINE_DATA_DIR`, default
  `./data/`) — nothing is sent anywhere except to Anthropic's API (for
  generating the brief) and to the connectors you've configured (for
  fetching public signals).
- Signals are deduped by URL so the same story doesn't get re-surfaced every
  run; `storage.Storage.unsurfaced_signals()` is the backlog the next run
  will consider.
- Review every draft before sending. This tool proposes outreach grounded in
  cited signals; it does not send anything itself.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```
