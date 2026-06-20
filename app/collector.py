from __future__ import annotations

from typing import Any

import feedparser


USER_AGENT = "jornal-nutri/0.1"


def fetch_feed_entries(feed_url: str) -> list[dict[str, Any]]:
    parsed = feedparser.parse(feed_url, agent=USER_AGENT)
    entries: list[dict[str, Any]] = []

    for entry in parsed.entries:
        title = str(getattr(entry, "title", "")).strip()
        if not title:
            continue

        content = ""
        if hasattr(entry, "summary"):
            content = str(entry.summary).strip()
        elif hasattr(entry, "description"):
            content = str(entry.description).strip()

        if not content:
            content = title

        entries.append(
            {
                "source": parsed.feed.get("title", "rss") if hasattr(parsed, "feed") else "rss",
                "url": str(getattr(entry, "link", "")).strip(),
                "title": title,
                "content": content,
                "published_at": str(getattr(entry, "published", "")).strip() or None,
            }
        )

    return [item for item in entries if item["url"]]
