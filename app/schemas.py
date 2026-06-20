from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texto original")
    source_language: str = Field(default="auto", description="Idioma de origem")


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str = "pt"


class NewsItem(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    source: str = Field(default="desconhecida")
    language: str = Field(default="auto")


class TranslatedNewsItem(BaseModel):
    title: str
    content: str
    source: str
    source_language: str
    target_language: str = "pt"


class ProcessedNewsItem(BaseModel):
    title: str
    content: str
    summary: str
    theme: str
    relevance_score: int
    source: str
    source_language: str
    target_language: str = "pt"
    summary_max_lines: int = 20


class StoredNewsItem(BaseModel):
    id: int
    source: str
    url: str
    title: str
    content: str
    summary: str
    theme: str
    relevance_score: int
    source_language: str
    target_language: str
    published_at: Optional[str] = None
    collected_at: str


class CollectResponse(BaseModel):
    feeds_checked: int
    entries_found: int
    entries_saved: int


class NewsletterResponse(BaseModel):
    file_path: str
    generated_items: int


class SettingsUpdateRequest(BaseModel):
    timezone: Optional[str] = None
    newsletter_hour: Optional[int] = Field(default=None, ge=0, le=23)
    newsletter_minute: Optional[int] = Field(default=None, ge=0, le=59)
    newsletter_min_score: Optional[int] = Field(default=None, ge=0, le=100)


class SettingsResponse(BaseModel):
    timezone: str
    newsletter_hour: int
    newsletter_minute: int
    newsletter_min_score: int
