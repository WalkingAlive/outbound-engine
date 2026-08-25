"""Two-way Slack DM interface.

Runs over Slack's Socket Mode, so no public HTTPS endpoint is required - it
works from a laptop, a personal server, or a container that only has
outbound network access. DM the bot the same commands as the CLI; `run`
also renders the resulting brief straight into the DM. See README "Slack
setup" for the one-time Slack app configuration.

Every DM is checked against SLACK_ALLOWED_USER_ID before anything runs -
this bot represents you (it spends your Anthropic/X API quota and can add
targets), so it must not respond to arbitrary workspace members.
"""

from __future__ import annotations

import io
import logging
import shlex
from contextlib import redirect_stderr, redirect_stdout

from outbound_engine.cli import build_parser
from outbound_engine.config import settings

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "*Outbound Engine* — DM me commands, same syntax as the CLI:\n"
    '• `add-target --name "Jane Doe" --type person --x-handle janedoe '
    '--keywords "seed round" "hiring"`\n'
    "• `list-targets`\n"
    '• `remove-target --name "Jane Doe"`\n'
    "• `add-repo /path/to/repo`\n"
    "• `run` — gather signals and generate today's brief now\n"
    "• `help` — this message"
)


def _run_cli(argv: list[str]) -> str:
    """Run a CLI-style command (any subcommand except `run`, `watch`, `slack`)
    and return whatever it would have printed/errored, for posting back to Slack.
    """
    parser = build_parser()
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            args = parser.parse_args(argv)
            args.func(args)
    except SystemExit:
        pass  # argparse errors/--help already wrote their message into buf
    except Exception as e:  # noqa: BLE001 - surface connector/agent errors back to the DM
        logger.exception("Slack command failed: %s", argv)
        return (buf.getvalue() + f"\nError: {e}").strip()
    return buf.getvalue().strip() or "Done."


def build_app():
    from slack_bolt import App

    if not settings.slack_bot_token:
        raise SystemExit("SLACK_BOT_TOKEN is required to run the Slack interface.")
    if not settings.slack_allowed_user_id:
        logger.warning(
            "SLACK_ALLOWED_USER_ID is not set - the bot will respond to ANY workspace "
            "member who DMs it. Set it to your Slack user ID before using this for real."
        )

    app = App(token=settings.slack_bot_token)

    @app.event("message")
    def on_message(event: dict, say) -> None:
        if event.get("channel_type") != "im":
            return  # only handle direct messages, never channels
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return  # ignore the bot's own messages

        user_id = event.get("user")
        if settings.slack_allowed_user_id and user_id != settings.slack_allowed_user_id:
            logger.warning("Ignored DM from unauthorized Slack user %s", user_id)
            say("This bot is private and isn't set up to respond to you.")
            return

        text = (event.get("text") or "").strip()
        if not text or text.lower() in ("help", "--help", "-h"):
            say(HELP_TEXT)
            return

        try:
            argv = shlex.split(text)
        except ValueError as e:
            say(f"Couldn't parse that: {e}")
            return

        if argv and argv[0] == "run":
            _handle_run(say)
            return

        say(_run_cli(argv))

    return app


def _handle_run(say) -> None:
    from outbound_engine.digest import run_daily_digest
    from outbound_engine.notifiers.slack import brief_to_blocks

    say("On it — gathering signals and writing today's brief...")
    try:
        brief = run_daily_digest()
    except Exception as e:  # noqa: BLE001
        logger.exception("Slack-triggered run failed")
        say(f"Run failed: {e}")
        return

    say(
        text=f"Outbound brief for {brief.generated_for}: {brief.summary}",
        blocks=brief_to_blocks(brief),
    )


def _start_background_digest(interval_hours: float) -> None:
    from apscheduler.schedulers.background import BackgroundScheduler

    from outbound_engine.digest import run_daily_digest
    from outbound_engine.notifiers.slack import post_brief

    scheduler = BackgroundScheduler()

    def _job() -> None:
        try:
            brief = run_daily_digest()
        except Exception:
            logger.exception("Scheduled digest run failed")
            return
        try:
            post_brief(brief)
        except Exception:
            logger.exception("Generated brief but failed to post it to Slack")

    scheduler.add_job(_job, "interval", hours=interval_hours)
    scheduler.start()
    logger.info("Background digest scheduled every %.1f hours.", interval_hours)


def run_socket_mode(background_interval_hours: float | None = None) -> None:
    """Start the bot and block. Optionally also push a brief to your DM on a cadence,
    so this single process covers both interactive chat and proactive delivery.
    """
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    if not settings.slack_app_token:
        raise SystemExit(
            "SLACK_APP_TOKEN is required (Socket Mode app-level token, starts with xapp-)."
        )

    app = build_app()

    if background_interval_hours:
        _start_background_digest(background_interval_hours)

    logger.info("Starting Slack Socket Mode handler...")
    SocketModeHandler(app, settings.slack_app_token).start()
