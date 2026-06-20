from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.config import DB_PATH


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT NOT NULL,
                theme TEXT NOT NULL DEFAULT 'geral',
                relevance_score INTEGER NOT NULL DEFAULT 0,
                source_language TEXT NOT NULL,
                target_language TEXT NOT NULL,
                published_at TEXT,
                collected_at TEXT NOT NULL
            )
            """
        )

        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(news)").fetchall()
        }
        if "theme" not in existing_columns:
            conn.execute("ALTER TABLE news ADD COLUMN theme TEXT NOT NULL DEFAULT 'geral'")
        if "relevance_score" not in existing_columns:
            conn.execute(
                "ALTER TABLE news ADD COLUMN relevance_score INTEGER NOT NULL DEFAULT 0"
            )

        conn.commit()
    finally:
        conn.close()


def upsert_news(item: dict[str, Any]) -> bool:
    init_db()
    now = datetime.now(timezone.utc).isoformat()

    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO news (
                source, url, title, content, summary, theme, relevance_score,
                source_language, target_language, published_at, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                source=excluded.source,
                title=excluded.title,
                content=excluded.content,
                summary=excluded.summary,
                theme=excluded.theme,
                relevance_score=excluded.relevance_score,
                source_language=excluded.source_language,
                target_language=excluded.target_language,
                published_at=excluded.published_at,
                collected_at=excluded.collected_at
            """,
            (
                item["source"],
                item["url"],
                item["title"],
                item["content"],
                item["summary"],
                item.get("theme", "geral"),
                int(item.get("relevance_score", 0)),
                item["source_language"],
                item["target_language"],
                item.get("published_at"),
                now,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def list_news(
    limit: int = 100,
    theme: Optional[str] = None,
    min_score: Optional[int] = None,
    offset: int = 0,
    search: Optional[str] = None,
) -> list[dict[str, Any]]:
    init_db()
    conn = _connect()
    try:
        conn.row_factory = sqlite3.Row

        query = """
            SELECT id, source, url, title, content, summary, theme, relevance_score,
                   source_language, target_language, published_at, collected_at
            FROM news
        """
        conditions: list[str] = []
        values: list[Any] = []

        if theme:
            conditions.append("theme = ?")
            values.append(theme)
        if min_score is not None:
            conditions.append("relevance_score >= ?")
            values.append(min_score)
        if search:
            conditions.append("(title LIKE ? OR content LIKE ? OR summary LIKE ?)")
            search_value = f"%{search}%"
            values.extend([search_value, search_value, search_value])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY relevance_score DESC, collected_at DESC LIMIT ? OFFSET ?"
        values.extend([limit, offset])

        rows = conn.execute(query, tuple(values)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def count_news(theme: Optional[str] = None, min_score: Optional[int] = None, search: Optional[str] = None) -> int:
    init_db()
    conn = _connect()
    try:
        query = "SELECT COUNT(*) FROM news"
        conditions: list[str] = []
        values: list[Any] = []

        if theme:
            conditions.append("theme = ?")
            values.append(theme)
        if min_score is not None:
            conditions.append("relevance_score >= ?")
            values.append(min_score)
        if search:
            conditions.append("(title LIKE ? OR content LIKE ? OR summary LIKE ?)")
            search_value = f"%{search}%"
            values.extend([search_value, search_value, search_value])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        row = conn.execute(query, tuple(values)).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()
