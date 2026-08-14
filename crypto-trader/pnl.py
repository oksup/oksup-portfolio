#!/usr/bin/env python3
"""Terminal PnL dashboard. Run: python pnl.py"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9
import sqlite3
import sys
from src.config import DB_PATH

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
rows = con.execute("SELECT * FROM trades ORDER BY ts ASC").fetchall()
con.close()

if not rows:
    print("No trades logged yet.")
    sys.exit(0)

W, RESET = "\033[1m", "\033[0m"
G, R, Y = "\033[32m", "\033[31m", "\033[33m"

total = len(rows)
by_signal = {"BUY": 0, "SELL": 0, "HOLD": 0}
filled = [r for r in rows if r["status"] == "FILLED"]
dry    = [r for r in rows if r["status"] == "DRY_RUN"]
skipped = [r for r in rows if r["status"] == "SKIPPED"]

for r in rows:
    by_signal[r["signal"]] = by_signal.get(r["signal"], 0) + 1

avg_conf = sum(r["confidence"] for r in rows) / total if total else 0
bullish_pct = by_signal["BUY"] / total * 100 if total else 0
bearish_pct = by_signal["SELL"] / total * 100 if total else 0

print(f"\n{W}{'═'*70}{RESET}")
print(f"{W}  CRYPTO TRADER — PnL DASHBOARD{RESET}")
print(f"{'═'*70}")

print(f"\n  {W}Signal Summary{RESET}")
print(f"  {'Total runs:':<22} {total}")
print(f"  {'BUY signals:':<22} {G}{by_signal['BUY']}{RESET}  ({bullish_pct:.0f}%)")
print(f"  {'SELL signals:':<22} {R}{by_signal['SELL']}{RESET}  ({bearish_pct:.0f}%)")
print(f"  {'HOLD/skipped:':<22} {Y}{by_signal['HOLD']}{RESET}")
print(f"  {'Avg confidence:':<22} {avg_conf:.0%}")
print(f"  {'Executed (filled):':<22} {len(filled)}")
print(f"  {'Dry-run logged:':<22} {len(dry)}")
print(f"  {'Skipped (threshold):':<22} {len(skipped)}")

if filled:
    print(f"\n  {W}Filled Orders{RESET}")
    print(f"  {'─'*66}")
    print(f"  {'Timestamp':<22} {'Side':<6} {'Price':>10}  {'Qty':>10}  {'Order ID'}")
    print(f"  {'─'*66}")
    for r in filled:
        ts = r["ts"][:19].replace("T", " ")
        side_color = G if r["side"] == "BUY" else R
        print(f"  {ts:<22} {side_color}{r['side']:<6}{RESET} ${r['price']:>9,.2f}  {r['qty']:>10.6f}  {r['order_id'] or '—'}")

from src.trader.portfolio import replay
pf = replay([dict(r) for r in rows])
if pf["equity_curve"]:
    pnl_color = G if pf["total_pnl"] >= 0 else R
    print(f"\n  {W}Paper Portfolio{RESET}")
    print(f"  {'Equity:':<22} ${pf['equity']:,.2f}  (start ${pf['starting_usdt']:,.0f})")
    print(f"  {'Total PnL:':<22} {pnl_color}${pf['total_pnl']:+,.2f}  ({pf['total_pnl_pct']:+.2f}%){RESET}")
    if pf["win_rate"] is not None:
        print(f"  {'Win rate:':<22} {pf['win_rate']:.0%}  ({pf['wins']}/{pf['closed']} closed)")
    if pf["open_qty"]:
        print(f"  {'Open position:':<22} {pf['open_qty']:.6f} BTC  (unrealized ${pf['unrealized']:+,.2f})")

from src.trader.scorecard import evaluate
sc = evaluate([dict(r) for r in rows])
sc_lines = []
for hname, h in sc["horizons"].items():
    if h["overall_accuracy"] is None:
        continue
    color = G if h["overall_accuracy"] >= 0.55 else (Y if h["overall_accuracy"] >= 0.45 else R)
    sc_lines.append(f"  {hname:<6} overall {color}{h['overall_accuracy']:.0%}{RESET}"
                    f"  (BUY {h['BUY']['correct']}/{h['BUY']['total']}, SELL {h['SELL']['correct']}/{h['SELL']['total']})")
if sc_lines:
    print(f"\n  {W}Signal Quality (was the call right N later?){RESET}")
    for line in sc_lines:
        print(line)

print(f"\n  {W}Last 5 Signals{RESET}")
print(f"  {'─'*66}")
recent = list(rows)[-5:][::-1]
for r in recent:
    ts = r["ts"][:19].replace("T", " ")
    sig = r["signal"]
    color = G if sig == "BUY" else (R if sig == "SELL" else Y)
    conf = f"{r['confidence']:.0%}"
    reason = (r["reasoning"] or "")[:38]
    print(f"  {ts}  {color}{sig:<5}{RESET} {conf:>4}  {reason}")

print(f"\n{'═'*70}\n")
