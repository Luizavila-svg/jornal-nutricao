from __future__ import annotations

from deep_translator import GoogleTranslator


class TranslationError(RuntimeError):
    pass


def translate_to_portuguese(text: str, source_language: str = "auto") -> str:
    if not text or not text.strip():
        return ""

    try:
        translator = GoogleTranslator(source=source_language, target="pt")
        return translator.translate(text)
    except Exception as exc:  # pragma: no cover
        raise TranslationError("Falha ao traduzir texto para português") from exc
