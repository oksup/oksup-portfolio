#!/usr/bin/env python3
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9
import sqlite3
import sys
from src.config import DB_PATH

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
rows = con.execute("SELECT * FROM trades ORDER BY ts DESC LIMIT ?", (n,)).fetchall()
con.close()

if not rows:
    print("No trades logged yet.")
    sys.exit(0)

# summary stats
total = len(rows)
buys  = sum(1 for r in rows if r["signal"] == "BUY")
sells = sum(1 for r in rows if r["signal"] == "SELL")
holds = sum(1 for r in rows if r["signal"] == "HOLD")

print(f"\n{'─'*80}")
print(f"  Last {total} signals  |  BUY {buys}  SELL {sells}  HOLD {holds}")
print(f"{'─'*80}")
print(f"  {'Timestamp':<26} {'Ticker':<10} {'Signal':<6} {'Conf':>5}  {'Status':<12}  Reasoning")
print(f"{'─'*80}")

SIGNAL_COLOR = {"BUY": "\033[32m", "SELL": "\033[31m", "HOLD": "\033[33m"}
RESET = "\033[0m"

for r in rows:
    ts = r["ts"][:19].replace("T", " ")
    sig = r["signal"]
    color = SIGNAL_COLOR.get(sig, "")
    conf = f"{r['confidence']:.0%}" if r["confidence"] is not None else "  — "
    reasoning = (r["reasoning"] or "")[:50]
    status = (r["status"] or "")[:12]
    print(f"  {ts:<26} {r['ticker']:<10} {color}{sig:<6}{RESET} {conf:>5}  {status:<12}  {reasoning}")

print(f"{'─'*80}\n")
