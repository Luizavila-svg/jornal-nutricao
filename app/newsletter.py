from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List

from app.config import DATA_DIR

NEWSLETTER_DIR = DATA_DIR / "newsletter"


def build_newsletter_markdown(items: List[Dict], for_date: date) -> str:
    lines = [
        f"# Newsletter Jornal Nutri - {for_date.isoformat()}",
        "",
        f"Total de noticias: {len(items)}",
        "",
    ]

    for item in items:
        lines.extend(
            [
                f"## {item['title']}",
                f"- Tema: {item.get('theme', 'geral')}",
                f"- Relevancia: {item.get('relevance_score', 0)}",
                f"- Fonte: {item.get('source', 'desconhecida')}",
                f"- Link: {item.get('url', '')}",
                "",
                "Resumo:",
                item.get("summary", ""),
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def write_daily_newsletter(items: List[Dict], for_date: date | None = None) -> Path:
    target_date = for_date or date.today()
    NEWSLETTER_DIR.mkdir(parents=True, exist_ok=True)

    path = NEWSLETTER_DIR / f"newsletter-{target_date.isoformat()}.md"
    content = build_newsletter_markdown(items, target_date)
    path.write_text(content, encoding="utf-8")
    return path
