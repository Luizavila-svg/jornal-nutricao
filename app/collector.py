from __future__ import annotations

import re
from typing import Any

import feedparser
from newspaper import Article


USER_AGENT = "jornal-nutri/0.1"
HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(text: str) -> str:
    text = HTML_TAG_RE.sub(" ", text)
    text = text.replace("\xa0", " ")
    return " ".join(text.split())


def _extract_full_article_text(url: str) -> str:
    try:
        article = Article(url=url, browser_user_agent=USER_AGENT)
        article.config.request_timeout = 10
        article.download()
        article.parse()
        extracted = _clean_text(article.text or "")
        if len(extracted) >= 300:
            return extracted
    except Exception:
        return ""

    return ""


def fetch_feed_entries(feed_url: str) -> list[dict[str, Any]]:
    try:
        parsed = feedparser.parse(feed_url, agent=USER_AGENT)
    except Exception:
        return []

    entries: list[dict[str, Any]] = []

    for entry in getattr(parsed, "entries", []):
        try:
            title = str(getattr(entry, "title", "")).strip()
            if not title:
                continue

            content = ""
            if hasattr(entry, "summary"):
                content = _clean_text(str(entry.summary).strip())
            elif hasattr(entry, "description"):
                content = _clean_text(str(entry.description).strip())

            url = str(getattr(entry, "link", "")).strip()
            full_content = _extract_full_article_text(url) if url else ""
            if full_content:
                content = f"{content} {full_content}".strip() if content else full_content

            if not content:
                content = title

            entries.append(
                {
                    "source": parsed.feed.get("title", "rss") if hasattr(parsed, "feed") else "rss",
                    "url": url,
                    "title": title,
                    "content": content,
                    "published_at": str(getattr(entry, "published", "")).strip() or None,
                }
            )
        except Exception:
            continue

    return [item for item in entries if item["url"]]
