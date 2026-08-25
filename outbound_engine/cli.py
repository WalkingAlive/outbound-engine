"""Command-line entry point.

Examples:
    python -m outbound_engine.cli add-target --name "Jane Doe" --type person \\
        --x-handle janedoe --keywords "raised seed" "hiring"
    python -m outbound_engine.cli add-repo ~/code/my-product
    python -m outbound_engine.cli run
    python -m outbound_engine.cli watch --interval-hours 24
"""

from __future__ import annotations

import argparse
import logging
import sys

from outbound_engine.models import Target
from outbound_engine.storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("outbound_engine.cli")


def cmd_add_target(args: argparse.Namespace) -> None:
    store = Storage()
    store.upsert_target(
        Target(
            name=args.name,
            type=args.type,
            keywords=args.keywords or [],
            linkedin_handle=args.linkedin_handle,
            x_handle=args.x_handle,
            notes=args.notes,
        )
    )
    print(f"Tracking {args.name} ({args.type}).")


def cmd_list_targets(args: argparse.Namespace) -> None:
    store = Storage()
    targets = store.list_targets()
    if not targets:
        print("No targets tracked yet.")
        return
    for t in targets:
        handles = []
        if t.linkedin_handle:
            handles.append(f"linkedin={t.linkedin_handle}")
        if t.x_handle:
            handles.append(f"x={t.x_handle}")
        print(f"- {t.name} ({t.type}) {' '.join(handles)}")


def cmd_remove_target(args: argparse.Namespace) -> None:
    store = Storage()
    removed = store.remove_target(args.name)
    print(f"Removed {args.name}." if removed else f"No such target: {args.name}")


def cmd_add_repo(args: argparse.Namespace) -> None:
    store = Storage()
    store.add_repo(args.path)
    print(f"Watching {args.path} for workspace context.")


def cmd_run(args: argparse.Namespace) -> None:
    from outbound_engine.config import settings
    from outbound_engine.digest import run_daily_digest

    if not settings.anthropic_api_key:
        print(
            "No ANTHROPIC_API_KEY configured. Set it in .env (see .env.example), "
            "or `export ANTHROPIC_API_KEY=...`, then retry.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    brief = run_daily_digest()
    print(f"Generated {len(brief.recommendations)} recommendation(s).")
    for rec in brief.recommendations:
        print(f"  - [{rec.priority}] {rec.target_name}: {rec.recommended_action}")
    _maybe_post_to_slack(brief)


def cmd_watch(args: argparse.Namespace) -> None:
    from outbound_engine.scheduler import run_forever

    run_forever(interval_hours=args.interval_hours)


def cmd_slack(args: argparse.Namespace) -> None:
    from outbound_engine.slack_app import run_socket_mode

    run_socket_mode(background_interval_hours=args.interval_hours)


def _maybe_post_to_slack(brief) -> None:
    from outbound_engine.notifiers import slack as slack_notifier

    if not slack_notifier.is_configured():
        return
    try:
        slack_notifier.post_brief(brief)
        print("Posted to your Slack DM.")
    except Exception as e:  # noqa: BLE001 - the brief is already saved; a Slack hiccup shouldn't fail the run
        print(f"Generated the brief but failed to post it to Slack: {e}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="outbound-engine")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add-target", help="Track a person or company")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--type", choices=["person", "company"], required=True)
    p_add.add_argument("--keywords", nargs="*", default=[])
    p_add.add_argument("--linkedin-handle")
    p_add.add_argument("--x-handle")
    p_add.add_argument("--notes")
    p_add.set_defaults(func=cmd_add_target)

    p_list = sub.add_parser("list-targets", help="List tracked targets")
    p_list.set_defaults(func=cmd_list_targets)

    p_rm = sub.add_parser("remove-target", help="Stop tracking a target")
    p_rm.add_argument("--name", required=True)
    p_rm.set_defaults(func=cmd_remove_target)

    p_repo = sub.add_parser("add-repo", help="Watch a local git repo for workspace context")
    p_repo.add_argument("path")
    p_repo.set_defaults(func=cmd_add_repo)

    p_run = sub.add_parser("run", help="Run one gather+brief cycle now")
    p_run.set_defaults(func=cmd_run)

    p_watch = sub.add_parser("watch", help="Run continuously on a schedule")
    p_watch.add_argument("--interval-hours", type=float, default=24.0)
    p_watch.set_defaults(func=cmd_watch)

    p_slack = sub.add_parser("slack", help="Start the Slack DM interface (Socket Mode)")
    p_slack.add_argument(
        "--interval-hours",
        type=float,
        default=None,
        help="Also push a brief to your DM on this cadence, in addition to on-demand commands",
    )
    p_slack.set_defaults(func=cmd_slack)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
