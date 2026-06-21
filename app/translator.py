from __future__ import annotations

from deep_translator import GoogleTranslator
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


class TranslationError(RuntimeError):
    pass


def _is_retryable_translation_error(exc: Exception) -> bool:
    message = str(exc).lower()
    transient_signals = (
        "429",
        "too many requests",
        "timeout",
        "timed out",
        "connection",
        "temporarily unavailable",
        "service unavailable",
        "502",
        "503",
        "504",
    )
    return any(token in message for token in transient_signals)


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception(_is_retryable_translation_error),
)
def _translate_with_retry(text: str, source_language: str) -> str:
    translator = GoogleTranslator(source=source_language, target="pt")
    return translator.translate(text)


def translate_to_portuguese(text: str, source_language: str = "auto") -> str:
    if not text or not text.strip():
        return ""

    try:
        return _translate_with_retry(text, source_language)
    except Exception as exc:  # pragma: no cover
        raise TranslationError("Falha ao traduzir texto para português") from exc
