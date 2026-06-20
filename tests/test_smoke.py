from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.summarizer import summarize_text_preserving_graphics


def _clean_db_file() -> None:
    db_file = Path(__file__).resolve().parent.parent / "data" / "jornal_nutri.db"
    if db_file.exists():
        db_file.unlink()

    settings_file = Path(__file__).resolve().parent.parent / "data" / "settings.json"
    if settings_file.exists():
        settings_file.unlink()


def test_health_endpoint() -> None:
    _clean_db_file()
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_summarizer_limits_to_20_lines() -> None:
    content = "\n".join([f"Linha {i}." for i in range(1, 70)])

    summary = summarize_text_preserving_graphics(content, max_lines=20, min_lines=15)

    assert len(summary.splitlines()) <= 20
    assert len(summary.splitlines()) >= 15


def test_summarizer_preserves_mermaid_and_image() -> None:
    content = """
Primeira frase importante sobre nutrição.
Segunda frase importante.

```mermaid
graph TD
A[Ingestao] --> B[Digestao]
```

![grafico](https://example.com/grafico.png)

Terceira frase.
""".strip()

    summary = summarize_text_preserving_graphics(content, max_lines=20, min_lines=15)

    assert "```mermaid" in summary
    assert "![grafico](https://example.com/grafico.png)" in summary


def test_api_news_empty_list() -> None:
    _clean_db_file()
    client = TestClient(app)

    response = client.get("/api/news")

    assert response.status_code == 200
    assert response.json() == []


def test_collect_and_list_news(monkeypatch) -> None:
    _clean_db_file()
    client = TestClient(app)

    monkeypatch.setattr("app.main.get_feed_urls", lambda: ["https://fake.feed/rss"])
    monkeypatch.setattr(
        "app.main.fetch_feed_entries",
        lambda _url: [
            {
                "source": "FakeFeed",
                "url": "https://example.com/noticia-1",
                "title": "Nutrition headline",
                "content": "Long content in english. Another sentence.",
                "published_at": "Sat, 20 Jun 2026 10:00:00 GMT",
            }
        ],
    )
    monkeypatch.setattr("app.main.translate_to_portuguese", lambda text, _lang: f"PT: {text}")

    collect_response = client.post("/collect")
    assert collect_response.status_code == 200
    assert collect_response.json()["entries_saved"] == 1

    news_response = client.get("/api/news")
    assert news_response.status_code == 200
    payload = news_response.json()
    assert len(payload) == 1
    assert payload[0]["title"].startswith("PT:")
    assert payload[0]["theme"] in {"clinica", "esportiva", "emagrecimento", "geral"}
    assert 0 <= payload[0]["relevance_score"] <= 100
    assert len(payload[0]["summary"].splitlines()) <= 30


def test_export_and_newsletter_endpoints(monkeypatch) -> None:
    _clean_db_file()
    client = TestClient(app)

    monkeypatch.setattr("app.main.get_feed_urls", lambda: ["https://fake.feed/rss"])
    monkeypatch.setattr(
        "app.main.fetch_feed_entries",
        lambda _url: [
            {
                "source": "FakeFeed",
                "url": "https://example.com/noticia-2",
                "title": "Clinical nutrition trial",
                "content": "Study with evidence and guideline details.",
                "published_at": "Sat, 20 Jun 2026 11:00:00 GMT",
            }
        ],
    )
    monkeypatch.setattr("app.main.translate_to_portuguese", lambda text, _lang: f"PT: {text}")

    collect_response = client.post("/collect")
    assert collect_response.status_code == 200

    csv_response = client.get("/export/csv")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "title" in csv_response.text

    xlsx_response = client.get("/export/xlsx")
    assert xlsx_response.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in xlsx_response.headers["content-type"]
    )

    newsletter_response = client.post("/newsletter/run")
    assert newsletter_response.status_code == 200
    body = newsletter_response.json()
    assert body["generated_items"] >= 0
    assert body["file_path"].endswith(".md")


def test_news_pagination_search_and_count(monkeypatch) -> None:
    _clean_db_file()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.main.get_feed_urls",
        lambda: ["https://fake.feed/rss", "https://fake.feed2/rss"],
    )
    monkeypatch.setattr(
        "app.main.fetch_feed_entries",
        lambda _url: [
            {
                "source": "FakeFeed",
                "url": "https://example.com/noticia-a",
                "title": "Clinical nutrition trial",
                "content": "Evidence and guideline for patient care.",
                "published_at": "Sat, 20 Jun 2026 12:00:00 GMT",
            },
            {
                "source": "FakeFeed",
                "url": "https://example.com/noticia-b",
                "title": "Sports whey and creatine",
                "content": "Athlete performance and training.",
                "published_at": "Sat, 20 Jun 2026 12:10:00 GMT",
            },
        ],
    )
    monkeypatch.setattr("app.main.translate_to_portuguese", lambda text, _lang: f"PT: {text}")

    collect_response = client.post("/collect")
    assert collect_response.status_code == 200

    count_response = client.get("/api/news/count")
    assert count_response.status_code == 200
    assert count_response.json()["total"] >= 2

    filtered_count = client.get("/api/news/count?theme=clinica")
    assert filtered_count.status_code == 200
    assert filtered_count.json()["total"] >= 1

    search_response = client.get("/api/news?q=creatine")
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert len(search_payload) >= 1
    assert any("creatine" in item["title"].lower() or "creatine" in item["content"].lower() for item in search_payload)

    page1 = client.get("/api/news?limit=1&offset=0")
    page2 = client.get("/api/news?limit=1&offset=1")
    assert page1.status_code == 200
    assert page2.status_code == 200
    assert len(page1.json()) == 1
    assert len(page2.json()) == 1
    assert page1.json()[0]["url"] != page2.json()[0]["url"]


def test_settings_get_and_update() -> None:
    _clean_db_file()
    client = TestClient(app)

    get_response = client.get("/api/settings")
    assert get_response.status_code == 200
    original = get_response.json()
    assert "timezone" in original

    update_response = client.put(
        "/api/settings",
        json={
            "timezone": "UTC",
            "newsletter_hour": 9,
            "newsletter_minute": 30,
            "newsletter_min_score": 65,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["timezone"] == "UTC"
    assert updated["newsletter_hour"] == 9
    assert updated["newsletter_minute"] == 30
    assert updated["newsletter_min_score"] == 65

    reset_response = client.post("/api/settings/reset")
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()
    assert reset_payload["timezone"]
    assert 0 <= reset_payload["newsletter_hour"] <= 23
    assert 0 <= reset_payload["newsletter_minute"] <= 59
    assert 0 <= reset_payload["newsletter_min_score"] <= 100
