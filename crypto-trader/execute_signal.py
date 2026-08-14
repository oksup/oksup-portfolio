#!/usr/bin/env python3
"""
Called by the Claude Routine after it generates a trading signal.
Logs the signal to SQLite and optionally places a testnet order.

All execution goes through src.trader.executor — the same risk rules
(stop-loss, trend filter, exposure cap, live-trading latch) apply here
exactly as they do to manual dashboard runs.

Usage:
  python3 execute_signal.py --signal BUY --confidence 0.85 \
    --reasoning "Strong bullish momentum" [--ticker BTCUSDT] [--dry-run]
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import argparse
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from src.config import TICKER, SIGNAL_CONFIDENCE_THRESHOLD
from src.trader.db import init_db, log_trade

parser = argparse.ArgumentParser()
parser.add_argument("--signal",     required=True, choices=["BUY", "SELL", "HOLD"])
parser.add_argument("--confidence", required=True, type=float)
parser.add_argument("--reasoning",  required=True)
parser.add_argument("--ticker",     default=TICKER)
parser.add_argument("--dry-run",    action="store_true")
args = parser.parse_args()

init_db()

# heartbeat — lets the dashboard show when the routine last actually ran
try:
    os.makedirs("data", exist_ok=True)
    with open("data/routine_heartbeat.txt", "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())
except OSError:
    pass

# fast offline path: HOLD / below-threshold never needs a price or network
if args.signal == "HOLD" or args.confidence < SIGNAL_CONFIDENCE_THRESHOLD:
    log_trade(args.ticker, args.signal, args.confidence, args.reasoning, status="SKIPPED")
    print(f"SKIPPED — signal={args.signal} confidence={args.confidence:.0%} (below threshold or HOLD)")
    sys.exit(0)

from src.trader.executor import execute

result = execute(
    {"signal": args.signal, "confidence": args.confidence, "reasoning": args.reasoning},
    args.ticker,
    dry_run=args.dry_run,
)

if result.get("error"):
    print(f"ERROR — {result['error']}", file=sys.stderr)
    sys.exit(1)
elif result.get("vetoed"):
    print(f"VETOED ({result['vetoed']}) — {args.signal} {args.ticker} blocked by risk rules")
elif result.get("action_taken"):
    mode = "DRY_RUN" if result.get("dry_run") else "FILLED"
    extra = f" — STOP-LOSS triggered" if result.get("stop_loss") else ""
    print(f"{mode} — {result['signal']} {args.ticker} @ ${result['price']:,.2f}{extra}")
else:
    print(f"SKIPPED — {result['signal']} @ confidence={result['confidence']:.0%}")
