"""
Running spend estimate.

Every model call appends one row to data/costs.csv. Nothing here can affect
a call: if logging fails, the call still happened and the bot carries on.

Why a CSV and not SQLite: this file is append-only and read once in a while.
A CSV opens in Numbers, survives a crash mid-write, and never takes a lock.
"""

from __future__ import annotations

import csv
import logging
import os
from collections import defaultdict
from datetime import datetime

from config import COST_LOG_ENABLED, COST_LOG_PATH, DATA_DIR, PRICES_PER_MTOK

log = logging.getLogger("costs")

HEADER = ["ts", "channel", "role", "model", "in_tokens", "out_tokens", "usd"]


def estimate_usd(model: str, in_tokens: int, out_tokens: int) -> float:
    """Zero for an unknown model rather than a guess. A wrong number is worse than none."""
    price = PRICES_PER_MTOK.get(model)
    if not price:
        return 0.0
    in_rate, out_rate = price
    return (in_tokens / 1_000_000) * in_rate + (out_tokens / 1_000_000) * out_rate


def record(channel: str, role: str, model: str, in_tokens: int, out_tokens: int) -> float:
    usd = estimate_usd(model, in_tokens, out_tokens)
    if not COST_LOG_ENABLED:
        return usd
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        new = not os.path.exists(COST_LOG_PATH)
        with open(COST_LOG_PATH, "a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if new:
                writer.writerow(HEADER)
            writer.writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    channel,
                    role,
                    model,
                    in_tokens,
                    out_tokens,
                    f"{usd:.6f}",
                ]
            )
    except Exception as exc:  # noqa: BLE001 - logging must never break a call
        log.warning("could not write cost log: %s", exc)
    return usd


def summary(days: int = 30) -> str:
    """Human-readable spend breakdown. Used by the spend_report tool."""
    if not os.path.exists(COST_LOG_PATH):
        return "No model calls logged yet."

    cutoff = datetime.now().timestamp() - days * 86400
    by_channel: dict[str, list] = defaultdict(lambda: [0, 0, 0.0])
    by_model: dict[str, float] = defaultdict(float)
    total = 0.0
    calls = 0

    with open(COST_LOG_PATH, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                when = datetime.fromisoformat(row["ts"]).timestamp()
            except (ValueError, KeyError):
                continue
            if when < cutoff:
                continue
            usd = float(row["usd"])
            bucket = by_channel[row["channel"]]
            bucket[0] += int(row["in_tokens"])
            bucket[1] += int(row["out_tokens"])
            bucket[2] += usd
            by_model[row["model"]] += usd
            total += usd
            calls += 1

    if not calls:
        return f"No model calls in the last {days} days."

    lines = [f"Last {days} days: **${total:.2f}** across {calls} calls."]
    lines.append("")
    lines.append("By channel:")
    for name, (tin, tout, usd) in sorted(by_channel.items(), key=lambda kv: -kv[1][2]):
        lines.append(f"  #{name:<10} ${usd:>7.3f}   {tin:,} in / {tout:,} out")
    lines.append("")
    lines.append("By model:")
    for name, usd in sorted(by_model.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {name:<38} ${usd:.3f}")

    monthly = total / max(days, 1) * 30
    lines.append("")
    lines.append(f"Run rate: about ${monthly:.2f}/month at this pace.")
    return "\n".join(lines)
