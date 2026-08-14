"""
Payments: QRIS with manual confirmation.

No payment gateway. Xendit and most aggregators want a business entity, and
this is a personal business. Bank Indonesia sets MDR for Usaha Mikro Individu
at 0% on transactions of Rp 500.000 or less, so collecting a Rp 39.000 ticket
by QRIS costs nothing at all. A gateway would cost more and do less.

The trade: a static QRIS code cannot notify anything. Confirmation is a human
step. You see the payment land in your banking app, you say so here, and
delivery fires. That is fine at low volume and it is the cheapest thing that
works today.

When volume makes that annoying, swap _record() for a provider callback. The
schemas and the channel scoping do not change. That is the wrapper pattern.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime

from config import DATA_DIR, PAYMENTS_DB_PATH, PRODUCT_PRICE_IDR
from tools import email as email_tool
from tools.base import tool

log = logging.getLogger("payments")


def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(PAYMENTS_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS payments (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               email TEXT NOT NULL,
               amount_idr INTEGER NOT NULL,
               method TEXT NOT NULL DEFAULT 'qris',
               reference TEXT DEFAULT '',
               paid_at TEXT NOT NULL DEFAULT (datetime('now')),
               delivered_at TEXT
           )"""
    )
    return conn


def _rupiah(amount: int) -> str:
    return f"Rp {amount:,}".replace(",", ".")


@tool(
    name="record_payment",
    description=(
        "Log a payment you have confirmed landed in your account. Use when you see a "
        "QRIS transfer arrive. Amount defaults to the product price if not given."
    ),
    parameters={
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Customer email address."},
            "amount_idr": {
                "type": "integer",
                "description": f"Rupiah received. Defaults to {PRODUCT_PRICE_IDR}.",
            },
            "reference": {
                "type": "string",
                "description": "Optional: transaction reference or sender name from the bank app.",
            },
        },
        "required": ["email"],
    },
)
def record_payment(email: str, amount_idr: int = 0, reference: str = "") -> str:
    if "@" not in email:
        return f"ERROR: '{email}' does not look like an email address."
    amount = int(amount_idr or PRODUCT_PRICE_IDR)

    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM payments WHERE email = ? AND paid_at > datetime('now', '-1 day')",
            (email,),
        ).fetchone()
        if existing:
            return (
                f"Already logged payment #{existing[0]} for {email} in the last 24h. "
                "Not logging a duplicate. Say `deliver report to <email>` if it needs sending."
            )
        cursor = conn.execute(
            "INSERT INTO payments (email, amount_idr, reference) VALUES (?, ?, ?)",
            (email, amount, reference),
        )
        payment_id = cursor.lastrowid

    short = amount != PRODUCT_PRICE_IDR
    note = (
        f"\nHeads up: that is {_rupiah(abs(PRODUCT_PRICE_IDR - amount))} "
        f"{'under' if amount < PRODUCT_PRICE_IDR else 'over'} the {_rupiah(PRODUCT_PRICE_IDR)} price."
        if short
        else ""
    )
    return (
        f"Payment #{payment_id} logged: {_rupiah(amount)} from {email}.{note}\n"
        f"Not delivered yet. Say `deliver report to {email}` when it is ready."
    )


@tool(
    name="list_payments",
    description="List recent payments and whether each has been delivered.",
    parameters={
        "type": "object",
        "properties": {
            "undelivered_only": {
                "type": "boolean",
                "description": "True to show only payments still waiting on delivery.",
            }
        },
        "required": [],
    },
)
def list_payments(undelivered_only: bool = False) -> str:
    query = "SELECT id, email, amount_idr, paid_at, delivered_at FROM payments"
    if undelivered_only:
        query += " WHERE delivered_at IS NULL"
    query += " ORDER BY id DESC LIMIT 25"

    with _conn() as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        return "No payments waiting." if undelivered_only else "No payments yet."

    lines = []
    for payment_id, email, amount, paid_at, delivered in rows:
        mark = "delivered" if delivered else "WAITING"
        lines.append(f"  #{payment_id:<3} [{mark:^9}] {_rupiah(amount):>10}  {email}  {paid_at[:10]}")
    return "\n".join(lines)


@tool(
    name="revenue_summary",
    description="Total revenue, customer count, and how many reports are still owed.",
    parameters={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Look back this many days. Default 30."}
        },
        "required": [],
    },
)
def revenue_summary(days: int = 30) -> str:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount_idr), 0), COUNT(DISTINCT email) "
            "FROM payments WHERE paid_at > datetime('now', ?)",
            (f"-{int(days)} days",),
        ).fetchone()
        owed = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE delivered_at IS NULL"
        ).fetchone()[0]
        lifetime = conn.execute("SELECT COALESCE(SUM(amount_idr), 0) FROM payments").fetchone()[0]

    count, total, customers = row
    if not count:
        return f"No payments in the last {days} days. Lifetime: {_rupiah(lifetime)}."

    lines = [
        f"Last {days} days: **{_rupiah(total)}** from {count} payment(s), {customers} customer(s).",
        f"Average: {_rupiah(int(total / count))}.",
        f"Lifetime: {_rupiah(lifetime)}.",
    ]
    if owed:
        lines.append(f"**{owed} report(s) not delivered yet.** Say: list payments waiting")
    # QRIS UMI is 0% MDR at or below Rp 500.000, so net equals gross here.
    lines.append("Fees: Rp 0. QRIS micro-merchant rate is 0% at this ticket size.")
    return "\n".join(lines)


@tool(
    name="deliver_report",
    description=(
        "Email a finished report to a paying customer and mark the payment delivered. "
        "Only use when the report content is ready."
    ),
    parameters={
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Customer email address."},
            "subject": {"type": "string", "description": "Email subject line, in Bahasa Indonesia."},
            "body_html": {
                "type": "string",
                "description": "The report as simple HTML. Use <p> and <h2> only.",
            },
        },
        "required": ["email", "subject", "body_html"],
    },
)
def deliver_report(email: str, subject: str, body_html: str) -> str:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, delivered_at FROM payments WHERE email = ? ORDER BY id DESC LIMIT 1",
            (email,),
        ).fetchone()

    if row is None:
        return (
            f"ERROR: no payment on record for {email}. "
            "Log the payment first, or this sends a paid report to someone who has not paid."
        )
    payment_id, delivered = row
    if delivered:
        return f"Payment #{payment_id} was already delivered on {delivered[:16]}. Not sending twice."

    result = email_tool.send(email, subject, body_html)
    if result.startswith("ERROR"):
        return f"{result}\nPayment #{payment_id} left marked as waiting."

    with _conn() as conn:
        conn.execute(
            "UPDATE payments SET delivered_at = datetime('now') WHERE id = ?", (payment_id,)
        )
    return f"Delivered to {email}. Payment #{payment_id} closed.\n{result}"
