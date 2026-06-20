from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

import httpx

from app.config import get_smtp_settings, get_telegram_settings


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

    response = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)
    response.raise_for_status()
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
