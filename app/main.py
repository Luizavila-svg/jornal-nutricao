from pathlib import Path
import csv
import io
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook

from app.collector import fetch_feed_entries
from app.config import get_feed_urls
from app.db import count_news, init_db, list_news, upsert_news
from app.newsletter import write_daily_newsletter
from app.notifier import notify_newsletter_generated
from app.scoring import classify_and_score
from app.schemas import (
    CollectResponse,
    NewsItem,
    NewsletterResponse,
    ProcessedNewsItem,
    SettingsResponse,
    SettingsUpdateRequest,
    StoredNewsItem,
    TranslateRequest,
    TranslateResponse,
)
from app.settings_store import get_default_settings, load_settings, reset_settings, save_settings
from app.summarizer import summarize_text_preserving_graphics
from app.translator import TranslationError, translate_to_portuguese

app = FastAPI(title="jornal-nutri", version="0.1.0")
scheduler = BackgroundScheduler(timezone="UTC")

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()
    if not scheduler.running:
        scheduler.start()
    _reschedule_newsletter_job()


@app.on_event("shutdown")
def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def _reschedule_newsletter_job() -> None:
    settings = load_settings()
    existing_job = scheduler.get_job("daily_newsletter")
    if existing_job is not None:
        scheduler.remove_job("daily_newsletter")

    scheduler.add_job(
        run_daily_newsletter,
        trigger="cron",
        hour=int(settings["newsletter_hour"]),
        minute=int(settings["newsletter_minute"]),
        timezone=settings["timezone"],
        id="daily_newsletter",
        replace_existing=True,
    )


def run_daily_newsletter() -> str:
    perform_collection()
    settings = load_settings()
    items = list_news(limit=200, min_score=int(settings["newsletter_min_score"]))
    file_path = write_daily_newsletter(items)
    notify_newsletter_generated(file_path=file_path, generated_items=len(items))
    return str(file_path)


@app.get("/api/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    settings = load_settings()
    return SettingsResponse(**settings)


@app.get("/api/settings/defaults", response_model=SettingsResponse)
def get_settings_defaults() -> SettingsResponse:
    return SettingsResponse(**get_default_settings())


@app.put("/api/settings", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdateRequest) -> SettingsResponse:
    merged = save_settings(payload.model_dump(exclude_none=True))
    _reschedule_newsletter_job()
    return SettingsResponse(**merged)


@app.post("/api/settings/reset", response_model=SettingsResponse)
def reset_settings_to_defaults() -> SettingsResponse:
    restored = reset_settings()
    _reschedule_newsletter_job()
    return SettingsResponse(**restored)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.post("/translate", response_model=TranslateResponse)
def translate_text(payload: TranslateRequest) -> TranslateResponse:
    try:
        translated = translate_to_portuguese(
            text=payload.text,
            source_language=payload.source_language,
        )
    except TranslationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranslateResponse(
        translated_text=translated,
        source_language=payload.source_language,
    )


@app.post("/news/process", response_model=ProcessedNewsItem)
def process_news_item(payload: NewsItem) -> ProcessedNewsItem:
    try:
        translated_title = translate_to_portuguese(payload.title, payload.language)
        translated_content = translate_to_portuguese(payload.content, payload.language)
    except TranslationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    summary = summarize_text_preserving_graphics(
        translated_content,
        max_lines=20,
        min_lines=15,
    )
    theme, relevance_score = classify_and_score(translated_title, translated_content)

    return ProcessedNewsItem(
        title=translated_title,
        content=translated_content,
        summary=summary,
        theme=theme,
        relevance_score=relevance_score,
        source=payload.source,
        source_language=payload.language,
    )


@app.post("/collect", response_model=CollectResponse)
def collect_news() -> CollectResponse:
    feeds_checked, entries_found, entries_saved = perform_collection()
    return CollectResponse(
        feeds_checked=feeds_checked,
        entries_found=entries_found,
        entries_saved=entries_saved,
    )


def perform_collection() -> tuple[int, int, int]:
    feed_urls = get_feed_urls()
    entries_found = 0
    entries_saved = 0

    for feed_url in feed_urls:
        try:
            entries = fetch_feed_entries(feed_url)
        except Exception as exc:
            print(f"[collect] feed_error url={feed_url} error={exc!r}")
            continue

        entries_found += len(entries)

        for entry in entries:
            try:
                translated_title = translate_to_portuguese(entry["title"], "auto")
                translated_content = translate_to_portuguese(entry["content"], "auto")
                summary = summarize_text_preserving_graphics(
                    translated_content,
                    max_lines=20,
                    min_lines=15,
                )
                theme, relevance_score = classify_and_score(translated_title, translated_content)
                saved = upsert_news(
                    {
                        "source": entry["source"],
                        "url": entry["url"],
                        "title": translated_title,
                        "content": translated_content,
                        "summary": summary,
                        "theme": theme,
                        "relevance_score": relevance_score,
                        "source_language": "auto",
                        "target_language": "pt",
                        "published_at": entry.get("published_at"),
                    }
                )
                if saved:
                    entries_saved += 1
            except Exception as exc:
                print(
                    f"[collect] entry_error url={entry.get('url')} title={entry.get('title')} error={exc!r}"
                )
                continue

    return len(feed_urls), entries_found, entries_saved


@app.get("/api/news", response_model=list[StoredNewsItem])
def get_news(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    theme: Optional[str] = None,
    min_score: Optional[int] = Query(default=None, ge=0, le=100),
    q: Optional[str] = None,
) -> list[StoredNewsItem]:
    rows = list_news(limit=limit, offset=offset, theme=theme, min_score=min_score, search=q)
    return [StoredNewsItem(**row) for row in rows]


@app.get("/api/news/count")
def get_news_count(
    theme: Optional[str] = None,
    min_score: Optional[int] = Query(default=None, ge=0, le=100),
    q: Optional[str] = None,
) -> dict[str, int]:
    total = count_news(theme=theme, min_score=min_score, search=q)
    return {"total": total}


@app.get("/export/csv")
def export_csv(
    theme: Optional[str] = None,
    min_score: Optional[int] = Query(default=None, ge=0, le=100),
) -> StreamingResponse:
    rows = list_news(limit=500, theme=theme, min_score=min_score)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "source",
            "url",
            "title",
            "summary",
            "theme",
            "relevance_score",
            "published_at",
            "collected_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["source"],
                row["url"],
                row["title"],
                row["summary"],
                row["theme"],
                row["relevance_score"],
                row["published_at"],
                row["collected_at"],
            ]
        )

    content = output.getvalue().encode("utf-8")
    filename = "jornal_nutri_export.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(content), media_type="text/csv", headers=headers)


@app.get("/export/xlsx")
def export_xlsx(
    theme: Optional[str] = None,
    min_score: Optional[int] = Query(default=None, ge=0, le=100),
) -> StreamingResponse:
    rows = list_news(limit=500, theme=theme, min_score=min_score)

    wb = Workbook()
    ws = wb.active
    ws.title = "noticias"
    ws.append(
        [
            "id",
            "source",
            "url",
            "title",
            "summary",
            "theme",
            "relevance_score",
            "published_at",
            "collected_at",
        ]
    )
    for row in rows:
        ws.append(
            [
                row["id"],
                row["source"],
                row["url"],
                row["title"],
                row["summary"],
                row["theme"],
                row["relevance_score"],
                row["published_at"],
                row["collected_at"],
            ]
        )

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    headers = {"Content-Disposition": 'attachment; filename="jornal_nutri_export.xlsx"'}
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.post("/newsletter/run", response_model=NewsletterResponse)
def run_newsletter_now() -> NewsletterResponse:
    perform_collection()
    settings = load_settings()
    items = list_news(limit=200, min_score=int(settings["newsletter_min_score"]))
    file_path = write_daily_newsletter(items)
    notify_newsletter_generated(file_path=file_path, generated_items=len(items))
    return NewsletterResponse(file_path=str(file_path), generated_items=len(items))
