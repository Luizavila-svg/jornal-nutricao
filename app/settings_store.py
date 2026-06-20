from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

from app.config import (
    DATA_DIR,
    get_newsletter_min_score,
    get_newsletter_schedule,
    get_newsletter_timezone,
)

SETTINGS_PATH = DATA_DIR / "settings.json"


def _defaults() -> Dict[str, Any]:
    hour, minute = get_newsletter_schedule()
    return {
        "timezone": get_newsletter_timezone(),
        "newsletter_hour": hour,
        "newsletter_minute": minute,
        "newsletter_min_score": get_newsletter_min_score(),
    }


def _normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = _defaults()
    settings.update(payload)

    timezone = str(settings["timezone"]).strip() or "America/Sao_Paulo"
    try:
        ZoneInfo(timezone)
    except Exception:
        timezone = "America/Sao_Paulo"
    settings["timezone"] = timezone
    settings["newsletter_hour"] = max(0, min(int(settings["newsletter_hour"]), 23))
    settings["newsletter_minute"] = max(0, min(int(settings["newsletter_minute"]), 59))
    settings["newsletter_min_score"] = max(0, min(int(settings["newsletter_min_score"]), 100))
    return settings


def load_settings() -> Dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return _defaults()

    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _defaults()
        return _normalize(raw)
    except Exception:
        return _defaults()


def save_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings()
    current.update(payload)
    normalized = _normalize(current)

    Path(SETTINGS_PATH).parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(normalized, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return normalized


def get_default_settings() -> Dict[str, Any]:
    return _defaults()


def reset_settings() -> Dict[str, Any]:
    defaults = _defaults()
    Path(SETTINGS_PATH).parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(defaults, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return defaults
