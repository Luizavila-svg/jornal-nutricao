from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "jornal_nutri.db"

DEFAULT_FEEDS = [
    "https://www.sciencedaily.com/rss/health_medicine/nutrition.xml",
    "https://www.hsph.harvard.edu/nutritionsource/feed/",
    "https://rss.sciencedirect.com/publication/science/09552863",
]


def get_feed_urls() -> list[str]:
    env_value = os.getenv("JORNAL_NUTRI_FEEDS", "").strip()
    if not env_value:
        return DEFAULT_FEEDS

    parsed = [item.strip() for item in env_value.split(",")]
    return [item for item in parsed if item]


def get_max_entries_per_feed() -> int:
    raw = os.getenv("JORNAL_NUTRI_MAX_ENTRIES_PER_FEED", "15").strip()
    try:
        value = int(raw)
    except ValueError:
        return 15
    return max(1, min(value, 100))


def get_newsletter_timezone() -> str:
    return os.getenv("JORNAL_NUTRI_TIMEZONE", "America/Sao_Paulo").strip()


def get_newsletter_schedule() -> tuple[int, int]:
    hour = int(os.getenv("JORNAL_NUTRI_NEWSLETTER_HOUR", "7"))
    minute = int(os.getenv("JORNAL_NUTRI_NEWSLETTER_MINUTE", "0"))
    return hour, minute


def get_newsletter_min_score() -> int:
    return int(os.getenv("JORNAL_NUTRI_NEWSLETTER_MIN_SCORE", "50"))


def get_smtp_settings() -> dict[str, str]:
    return {
        "host": os.getenv("JORNAL_NUTRI_SMTP_HOST", "").strip(),
        "port": os.getenv("JORNAL_NUTRI_SMTP_PORT", "587").strip(),
        "user": os.getenv("JORNAL_NUTRI_SMTP_USER", "").strip(),
        "password": os.getenv("JORNAL_NUTRI_SMTP_PASSWORD", "").strip(),
        "from": os.getenv("JORNAL_NUTRI_SMTP_FROM", "").strip(),
        "to": os.getenv("JORNAL_NUTRI_SMTP_TO", "").strip(),
    }


def get_telegram_settings() -> dict[str, str]:
    return {
        "bot_token": os.getenv("JORNAL_NUTRI_TELEGRAM_BOT_TOKEN", "").strip(),
        "chat_id": os.getenv("JORNAL_NUTRI_TELEGRAM_CHAT_ID", "").strip(),
    }
