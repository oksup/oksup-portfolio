"""
Transactional email via Brevo.

Personal Brevo account only. The Nakula account and its lists are a work
asset and must never be used for this product.

Free tier is 300 emails/day, which covers launch and then some. No new
dependency: stdlib urllib, so nothing to install and nothing to break.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime

from config import BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME, DATA_DIR
from tools.base import tool

log = logging.getLogger("email")

API_URL = "https://api.brevo.com/v3/smtp/email"
SEND_LOG = os.path.join(DATA_DIR, "sent_email.log")


def _log_send(to: str, subject: str, outcome: str) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SEND_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat(timespec='seconds')}\t{to}\t{subject}\t{outcome}\n")
    except OSError as exc:
        log.warning("could not write send log: %s", exc)


def send(to: str, subject: str, html: str, to_name: str = "") -> str:
    """
    Plain function, not a tool. Used by the payments flow to deliver a report
    without going through the model a second time.

    Returns "OK ..." or "ERROR ...". Never raises.
    """
    if not BREVO_API_KEY:
        return "ERROR: BREVO_API_KEY is not set in .env. Nothing was sent."
    if not BREVO_SENDER_EMAIL:
        return "ERROR: BREVO_SENDER_EMAIL is not set in .env. Nothing was sent."

    payload = {
        "sender": {"email": BREVO_SENDER_EMAIL, "name": BREVO_SENDER_NAME},
        "to": [{"email": to, "name": to_name or to.split("@")[0]}],
        "subject": subject,
        "htmlContent": html,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8") or "{}")
        message_id = body.get("messageId", "sent")
        _log_send(to, subject, f"ok {message_id}")
        return f"OK. Sent to {to} ({message_id})."
    except urllib.error.HTTPError as exc:
        # Print what Brevo actually said. A 401 and a 400 need different fixes
        # and "failed" tells you neither.
        detail = exc.read().decode("utf-8", "replace")[:400]
        _log_send(to, subject, f"http {exc.code}")
        return f"ERROR: Brevo returned {exc.code}. {detail}"
    except Exception as exc:  # noqa: BLE001
        _log_send(to, subject, f"error {exc}")
        return f"ERROR: could not reach Brevo: {exc}"


# NOTE: there is deliberately no raw `send_email` tool.
#
# deliver_report in payments.py refuses to send to an address with no payment
# on record. A general-purpose send tool sitting next to it in the same channel
# would let the model route around that check, and the check is the only thing
# stopping a paid report going out free. Email sending is reachable through
# deliver_report and nowhere else.


@tool(
    name="email_status",
    description="Show whether email sending is configured, and the last few sends.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def email_status() -> str:
    lines = []
    lines.append(f"API key:  {'set' if BREVO_API_KEY else 'MISSING (set BREVO_API_KEY in .env)'}")
    lines.append(
        f"Sender:   {BREVO_SENDER_EMAIL or 'MISSING (set BREVO_SENDER_EMAIL in .env)'}"
    )
    if not os.path.exists(SEND_LOG):
        lines.append("No emails sent yet.")
        return "\n".join(lines)
    with open(SEND_LOG, encoding="utf-8") as fh:
        recent = fh.readlines()[-5:]
    lines.append("")
    lines.append("Recent:")
    for row in recent:
        ts, to, subject, outcome = (row.rstrip("\n").split("\t") + ["", "", ""])[:4]
        lines.append(f"  {ts}  {to}  {subject[:30]}  {outcome}")
    return "\n".join(lines)
