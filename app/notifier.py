from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import get_smtp_settings, get_telegram_settings


def _is_retryable_telegram_error(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or 500 <= status_code < 600
    return False


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception(_is_retryable_telegram_error),
)
def _post_telegram_message(url: str, payload: dict[str, str]) -> None:
    response = httpx.post(url, json=payload, timeout=20)
    response.raise_for_status()


def _send_email(file_path: Path, generated_items: int) -> bool:
    smtp = get_smtp_settings()
    required = [smtp["host"], smtp["user"], smtp["password"], smtp["from"], smtp["to"]]
    if not all(required):
        return False

    message = EmailMessage()
    message["Subject"] = "Newsletter Jornal Nutri"
    message["From"] = smtp["from"]
    message["To"] = smtp["to"]
    message.set_content(
        f"Newsletter gerada com {generated_items} itens.\nArquivo: {file_path}"
    )

    port = int(smtp["port"])
    with smtplib.SMTP(smtp["host"], port) as server:
        server.starttls()
        server.login(smtp["user"], smtp["password"])
        server.send_message(message)

    return True


def _send_telegram(file_path: Path, generated_items: int) -> bool:
    telegram = get_telegram_settings()
    token = telegram["bot_token"]
    chat_id = telegram["chat_id"]
    if not token or not chat_id:
        return False

    text = f"Newsletter gerada com {generated_items} itens. Arquivo: {file_path}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    _post_telegram_message(url, {"chat_id": chat_id, "text": text})
    return True


def notify_newsletter_generated(file_path: Path, generated_items: int) -> dict[str, bool]:
    email_sent = False
    telegram_sent = False

    try:
        email_sent = _send_email(file_path, generated_items)
    except Exception:
        email_sent = False

    try:
        telegram_sent = _send_telegram(file_path, generated_items)
    except Exception:
        telegram_sent = False

    return {"email_sent": email_sent, "telegram_sent": telegram_sent}
