"""Proactive cadence for the agent.

Two supported ways to run this on a schedule:
1. `python -m outbound_engine.cli watch` - a long-lived process using
   APScheduler, for a container/VM you keep running.
2. A plain cron job / systemd timer calling
   `python -m outbound_engine.cli run` - simpler, no long-lived process,
   preferred for most deployments. See README for a crontab example.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_forever(interval_hours: float = 24.0) -> None:
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError as e:
        raise SystemExit(
            "`watch` requires apscheduler. Install it with `pip install apscheduler`, "
            "or run `python -m outbound_engine.cli run` from cron/systemd instead."
        ) from e

    from outbound_engine.digest import run_daily_digest

    scheduler = BlockingScheduler()

    def _job() -> None:
        try:
            brief = run_daily_digest()
            logger.info("Digest run complete: %d recommendation(s).", len(brief.recommendations))
        except Exception:
            logger.exception("Digest run failed")

    scheduler.add_job(_job, "interval", hours=interval_hours)
    logger.info("Running once immediately, then every %.1f hours...", interval_hours)
    _job()
    scheduler.start()
