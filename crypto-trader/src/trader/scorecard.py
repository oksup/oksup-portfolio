"""
Signal-quality scorecard — was the analyzer actually right?

For every BUY/SELL signal in the trade log, looks up what the price did
1h / 4h / 24h later (using the log's own price series — no network, works
for both simulated and live data) and scores the call:

- BUY  is correct if the later price is higher
- SELL is correct if the later price is lower

This answers the question that decides everything else about the project:
does the sentiment signal have any predictive edge, or is it noise?
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

from datetime import datetime

HORIZONS = {"1h": 3600, "4h": 14400, "24h": 86400}
# a price point qualifies for a horizon if it lands in [h, h + slack]
SLACK_FRACTION = 0.75


def _epoch(ts: str) -> float:
    return datetime.fromisoformat(ts).timestamp()


def evaluate(trades: list, horizons: dict = None) -> dict:
    """trades: rows from the trades table, any order/status. Returns per-horizon
    accuracy and average move for BUY and SELL signals."""
    horizons = horizons or HORIZONS
    priced = sorted((t for t in trades if t.get("price")), key=lambda t: t["ts"])
    # one price series per asset — multi-asset logs must not cross-contaminate
    by_ticker = {}
    for t in priced:
        by_ticker.setdefault(t.get("ticker"), []).append((_epoch(t["ts"]), float(t["price"])))

    results = {name: {"BUY": [], "SELL": []} for name in horizons}
    pending = 0

    for t in priced:
        if t["signal"] not in ("BUY", "SELL"):
            continue
        series = by_ticker.get(t.get("ticker"), [])
        t0, p0 = _epoch(t["ts"]), float(t["price"])
        for name, secs in horizons.items():
            later = next(
                (p for e, p in series if t0 + secs <= e <= t0 + secs * (1 + SLACK_FRACTION)),
                None,
            )
            if later is None:
                pending += 1
                continue
            move_pct = (later / p0 - 1) * 100
            correct = move_pct > 0 if t["signal"] == "BUY" else move_pct < 0
            results[name][t["signal"]].append({"correct": correct, "move_pct": move_pct})

    out = {"horizons": {}, "pending": pending}
    for name in horizons:
        row = {}
        for side in ("BUY", "SELL"):
            calls = results[name][side]
            row[side] = {
                "total": len(calls),
                "correct": sum(1 for c in calls if c["correct"]),
                "accuracy": (sum(1 for c in calls if c["correct"]) / len(calls)) if calls else None,
                "avg_move_pct": (sum(c["move_pct"] for c in calls) / len(calls)) if calls else None,
            }
        both = results[name]["BUY"] + results[name]["SELL"]
        row["overall_accuracy"] = (sum(1 for c in both if c["correct"]) / len(both)) if both else None
        out["horizons"][name] = row
    return out
