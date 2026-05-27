from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"


class ConfigError(RuntimeError):
    pass


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value or ""


def get_int_env(name: str, default: int) -> int:
    raw_value = get_env(name, str(default))
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw_value!r}") from exc


def parse_recipients(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    tavily_api_key: str
    openai_api_key: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    gmail_sender_email: str
    newsletter_default_recipients: list[str]
    newsletter_from_name: str
    openai_text_model: str
    newsletter_search_depth: str
    newsletter_max_results: int


def load_settings(require_live: bool = False, require_gmail: bool = False) -> Settings:
    load_dotenv()
    return Settings(
        tavily_api_key=get_env("TAVILY_API_KEY", required=require_live),
        openai_api_key=get_env("OPENAI_API_KEY", required=require_live),
        google_client_id=get_env("GOOGLE_CLIENT_ID", required=require_gmail),
        google_client_secret=get_env("GOOGLE_CLIENT_SECRET", required=require_gmail),
        google_refresh_token=get_env("GOOGLE_REFRESH_TOKEN", required=require_gmail),
        gmail_sender_email=get_env("GMAIL_SENDER_EMAIL", required=require_gmail),
        newsletter_default_recipients=parse_recipients(get_env("NEWSLETTER_DEFAULT_RECIPIENTS")),
        newsletter_from_name=get_env("NEWSLETTER_FROM_NAME", "Agentic Brief"),
        openai_text_model=get_env("OPENAI_TEXT_MODEL", "gpt-4.1-mini"),
        newsletter_search_depth=get_env("NEWSLETTER_SEARCH_DEPTH", "basic"),
        newsletter_max_results=get_int_env("NEWSLETTER_MAX_RESULTS", 5),
    )
