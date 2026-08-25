"""Environment-driven configuration. No secrets are hardcoded anywhere in this project."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set directly.

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("OUTBOUND_ENGINE_DATA_DIR", BASE_DIR / "data"))
OUTPUT_DIR = Path(os.environ.get("OUTBOUND_ENGINE_OUTPUT_DIR", BASE_DIR / "output"))
DB_PATH = DATA_DIR / "outbound_engine.db"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")
    claude_model: str = os.environ.get("OUTBOUND_ENGINE_MODEL", "claude-opus-5")
    x_bearer_token: str | None = os.environ.get("X_BEARER_TOKEN")
    linkedin_provider_module: str | None = os.environ.get(
        "LINKEDIN_PROVIDER_MODULE"
    )  # dotted path to a class implementing linkedin.LinkedInProvider, e.g. "myco.providers.Proxycurl"
    user_name: str = os.environ.get("OUTBOUND_ENGINE_USER_NAME", "you")
    news_results_per_target: int = int(
        os.environ.get("OUTBOUND_ENGINE_NEWS_LIMIT", "5")
    )
    web_request_timeout: float = float(
        os.environ.get("OUTBOUND_ENGINE_HTTP_TIMEOUT", "10")
    )
    workspace_git_days: int = int(os.environ.get("OUTBOUND_ENGINE_GIT_DAYS", "7"))

    # Slack DM interface (see README "Slack setup"). All three are required
    # for the bot; slack_bot_token + slack_allowed_user_id alone are enough
    # for one-way brief delivery from `run`/`watch` without the chat bot.
    slack_bot_token: str | None = os.environ.get("SLACK_BOT_TOKEN")  # xoxb-...
    slack_app_token: str | None = os.environ.get("SLACK_APP_TOKEN")  # xapp-..., Socket Mode
    slack_allowed_user_id: str | None = os.environ.get("SLACK_ALLOWED_USER_ID")


settings = Settings()


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
