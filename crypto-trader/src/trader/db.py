from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9
from typing import Optional
import sqlite3
from datetime import datetime, timezone
from src.config import DB_PATH


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT NOT NULL,
            ticker    TEXT NOT NULL,
            signal    TEXT NOT NULL,
            confidence REAL NOT NULL,
            reasoning TEXT,
            price     REAL,
            qty       REAL,
            side      TEXT,
            order_id  TEXT,
            status    TEXT
        )
    """)
    con.commit()
    con.close()


def log_trade(
    ticker: str,
    signal: str,
    confidence: float,
    reasoning: str,
    price: Optional[float] = None,
    qty: Optional[float] = None,
    side: Optional[str] = None,
    order_id: Optional[str] = None,
    status: str = "LOGGED",
):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT INTO trades (ts, ticker, signal, confidence, reasoning, price, qty, side, order_id, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now(timezone.utc).isoformat(), ticker, signal, confidence, reasoning,
         price, qty, side, order_id, status),
    )
    con.commit()
    con.close()


def all_trades() -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM trades ORDER BY ts ASC").fetchall()
    con.close()
    return [dict(r) for r in rows]


def recent_trades(n: int = 10) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM trades ORDER BY ts DESC LIMIT ?", (n,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]
