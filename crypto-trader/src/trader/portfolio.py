"""
Paper-portfolio replay — computes simulated PnL from the trade log.

Pure read-side: no schema changes, no state files. Replays acted-on signals
(DRY_RUN / FILLED) in chronological order against their logged prices:

- BUY opens or adds to a long position, sized at MAX_ORDER_USDT notional
  (or the logged qty when present, i.e. real testnet fills)
- SELL closes the entire open position and realizes PnL
- HOLD / SKIPPED rows are ignored

Returns the equity curve, realized PnL, win rate, and open-position state,
so the dashboard and CLI can answer the only question that matters:
"would this strategy have made money?"
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

from src.config import MAX_ORDER_USDT, FEE_RATE

STARTING_USDT = 10_000.0


def replay(trades: list, starting_usdt: float = STARTING_USDT, ticker: str = None) -> dict:
    """trades: rows from the trades table, any order. Acts on DRY_RUN/FILLED only.
    Pass ticker to replay a single asset (multi-asset logs would otherwise mix prices)."""
    acted = sorted(
        (t for t in trades if t["status"] in ("DRY_RUN", "FILLED") and t["price"]
         and (ticker is None or t["ticker"] == ticker)),
        key=lambda t: t["ts"],
    )

    usdt = starting_usdt
    position_qty = 0.0
    position_cost = 0.0          # USDT spent on the open position
    realized = []                # list of {ts, pnl, pct}
    equity_curve = []            # list of {ts, equity, price}

    for t in acted:
        price = float(t["price"])
        if t["signal"] == "BUY":
            notional = float(t["qty"]) * price if t["qty"] else min(MAX_ORDER_USDT, usdt)
            if notional <= 0 or usdt < notional:
                notional = usdt  # all-in cap; skip if broke
            if notional > 0:
                qty = notional * (1 - FEE_RATE) / price  # taker fee shrinks the fill
                usdt -= notional
                position_qty += qty
                position_cost += notional
        elif t["signal"] == "SELL" and position_qty > 0:
            proceeds = position_qty * price * (1 - FEE_RATE)
            pnl = proceeds - position_cost
            realized.append({
                "ts": t["ts"],
                "pnl": pnl,
                "pct": (pnl / position_cost * 100) if position_cost else 0.0,
            })
            usdt += proceeds
            position_qty = 0.0
            position_cost = 0.0

        equity_curve.append({
            "ts": t["ts"],
            "equity": usdt + position_qty * price,
            "price": price,
        })

    last_price = acted[-1]["price"] if acted else None
    equity = usdt + position_qty * (last_price or 0)
    wins = [r for r in realized if r["pnl"] > 0]

    return {
        "starting_usdt": starting_usdt,
        "equity": equity,
        "total_pnl": equity - starting_usdt,
        "total_pnl_pct": (equity / starting_usdt - 1) * 100,
        "realized_trades": realized,
        "closed": len(realized),
        "wins": len(wins),
        "win_rate": (len(wins) / len(realized)) if realized else None,
        "open_qty": position_qty,
        "open_cost": position_cost,
        "unrealized": (position_qty * last_price - position_cost) if (position_qty and last_price) else 0.0,
        "equity_curve": equity_curve,
    }
