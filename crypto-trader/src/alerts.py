from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9
from typing import Optional
import os
import requests
from datetime import datetime, timezone


def _slack(message: str):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return
    requests.post(url, json={"text": message}, timeout=5)


def _email(message: str, subject: str):
    api_key = os.getenv("SENDGRID_API_KEY")
    to_email = os.getenv("ALERT_EMAIL")
    from_email = os.getenv("FROM_EMAIL", to_email)
    if not all([api_key, to_email, from_email]):
        return
    requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": message}],
        },
        timeout=10,
    )


def notify(signal: str, ticker: str, confidence: float, reasoning: str, price: Optional[float], status: str):
    if signal == "HOLD" or status == "SKIPPED":
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    emoji = "🟢" if signal == "BUY" else "🔴"
    price_str = f"${price:,.2f}" if price else "N/A"
    msg = (
        f"{emoji} {signal} {ticker} @ {price_str}\n"
        f"Confidence: {confidence:.0%} | {ts}\n"
        f"Reason: {reasoning}\n"
        f"Status: {status}"
    )
    subject = f"[Crypto Trader] {signal} {ticker} — {confidence:.0%} confidence"

    _slack(msg)
    _email(msg, subject)
