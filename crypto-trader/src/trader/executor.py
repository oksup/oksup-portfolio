from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

from src.config import (
    TICKER, SIGNAL_CONFIDENCE_THRESHOLD, MAX_ORDER_USDT,
    MAX_OPEN_USDT, STOP_LOSS_PCT, TAKE_PROFIT_PCT, TREND_FILTER,
    ADAPTIVE_THRESHOLD, ML_GATE, ML_MIN_PROB,
    BINANCE_TESTNET, ALLOW_LIVE_TRADING,
)
from src import assets, market
from src.ml import learner
from src.trader import binance_client, db
from src import alerts


def _sma(ticker: str, periods: int = 20, interval: str = "15m"):
    """Moving average via the unified market provider (crypto + stocks).
    Returns None on failure — the trend filter then stands aside."""
    return market.get_sma(ticker, periods, interval)


def _side_threshold(signal: str, trades: list) -> tuple:
    """(threshold, reason) — raises the confidence bar for a signal side while
    its rolling 4h scorecard accuracy is under 50% (min 10 scored calls).
    Turns the scorecard from a report into a decision input."""
    base = SIGNAL_CONFIDENCE_THRESHOLD
    if not ADAPTIVE_THRESHOLD or signal not in ("BUY", "SELL"):
        return base, None
    try:
        from src.trader.scorecard import evaluate
        h = evaluate(trades)["horizons"].get("4h", {}).get(signal)
    except Exception:
        return base, None
    if h and h["total"] >= 10 and h["accuracy"] is not None and h["accuracy"] < 0.5:
        raised = min(0.95, base + 0.15)
        return raised, (f"{signal} calls only {h['accuracy']:.0%} accurate over last "
                        f"{h['total']} (4h) — bar raised to {raised:.0%}")
    return base, None


def _open_position(ticker: str, trades: list = None) -> tuple:
    """(open_qty, open_cost) of this asset's paper position, from the trade log."""
    from src.trader.portfolio import replay
    pf = replay(trades if trades is not None else db.all_trades(), ticker=ticker)
    return pf["open_qty"], pf["open_cost"]


def execute(analysis: dict, ticker: str = TICKER, dry_run: bool = False) -> dict:
    signal = analysis["signal"]          # BUY | SELL | HOLD
    confidence = analysis["confidence"]
    reasoning = analysis["reasoning"]

    crypto = assets.is_crypto(ticker)
    paper_only = not crypto
    if paper_only:
        dry_run = True  # stocks have no execution venue here — always paper

    if crypto:
        try:
            client = binance_client.get_client()
            price = binance_client.get_price(ticker, client)
        except Exception:
            if not dry_run:
                raise  # live orders need a working authenticated client
            client = None
            price = market.get_price(ticker)
    else:
        client = None
        price = market.get_price(ticker)

    if price is None:
        db.log_trade(ticker, signal, confidence,
                     f"No price available for {ticker} — run aborted. {reasoning}",
                     status="ERROR: no price")
        return {"signal": signal, "confidence": confidence, "reasoning": reasoning,
                "price": None, "action_taken": False, "error": f"no price for {ticker}"}

    # ── keep learning: fold newly matured outcomes into the model every run ──
    trades = db.all_trades()
    try:
        ml_train = learner.update_model(trades)
    except Exception:
        ml_train = None

    result = {
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "price": price,
        "action_taken": False,
        "paper_only": paper_only,
    }
    if ml_train and ml_train["new"]:
        result["ml_learned"] = ml_train["new"]

    open_qty, open_cost = _open_position(ticker, trades)

    # ── forced exits: override the signal based on the open position.
    # Stop-loss cuts losers early; take-profit banks winners before sentiment
    # noise gives them back. Together they shape the asymmetric reward/risk
    # (default 4% TP vs 2.5% SL ≈ 1.6:1) that drives positive expectancy.
    if open_qty > 0 and open_cost > 0:
        avg_cost = open_cost / open_qty
        move_pct = (price / avg_cost - 1) * 100
        if STOP_LOSS_PCT > 0 and move_pct <= -STOP_LOSS_PCT:
            signal, confidence = "SELL", 1.0
            reasoning = (f"STOP-LOSS: position down {-move_pct:.1f}% from "
                         f"${avg_cost:,.2f} cost basis (limit {STOP_LOSS_PCT:.1f}%). "
                         f"Original signal: {result['signal']}")
            result.update(signal=signal, confidence=confidence,
                          reasoning=reasoning, stop_loss=True)
        elif TAKE_PROFIT_PCT > 0 and move_pct >= TAKE_PROFIT_PCT:
            signal, confidence = "SELL", 1.0
            reasoning = (f"TAKE-PROFIT: position up {move_pct:.1f}% from "
                         f"${avg_cost:,.2f} cost basis (target {TAKE_PROFIT_PCT:.1f}%). "
                         f"Original signal: {result['signal']}")
            result.update(signal=signal, confidence=confidence,
                          reasoning=reasoning, take_profit=True)

    forced_exit = result.get("stop_loss") or result.get("take_profit")

    # ── adaptive per-side threshold: the scorecard sets the bar ──
    threshold, raised_why = (SIGNAL_CONFIDENCE_THRESHOLD, None) if forced_exit \
        else _side_threshold(signal, trades)
    if signal == "HOLD" or confidence < threshold:
        if raised_why and signal != "HOLD" and confidence >= SIGNAL_CONFIDENCE_THRESHOLD:
            reasoning = f"Adaptive threshold: {raised_why}. {reasoning}"
            result["adaptive_skip"] = True
        db.log_trade(ticker, signal, confidence, reasoning, price=price, status="SKIPPED")
        result["reasoning"] = reasoning
        return result

    # ── BUY-side risk vetoes (stop-loss SELLs are never vetoed) ──
    if signal == "BUY":
        # trend filter: don't buy into a downtrend
        if TREND_FILTER:
            sma = _sma(ticker)
            if sma is not None and price < sma:
                msg = (f"Trend filter: price ${price:,.2f} below 20-period "
                       f"SMA ${sma:,.2f} — BUY vetoed. {reasoning}")
                db.log_trade(ticker, signal, confidence, msg, price=price, status="VETOED_TREND")
                result["vetoed"] = "trend"
                return result
        # exposure cap: never hold more than MAX_OPEN_USDT at risk
        if open_cost >= MAX_OPEN_USDT:
            msg = (f"Exposure cap: ${open_cost:,.0f} already open "
                   f"(limit ${MAX_OPEN_USDT:,.0f}) — BUY vetoed. {reasoning}")
            db.log_trade(ticker, signal, confidence, msg, price=price, status="VETOED_RISK")
            result["vetoed"] = "exposure"
            return result

    # ── ML gate: the learner scores the signal from its own track record ──
    # (forced exits are never gated — risk management outranks the model)
    ml = None
    if ML_GATE and not forced_exit:
        try:
            ml = learner.assess(trades, ticker, signal, confidence, price)
        except Exception:
            ml = None
        if ml:
            result["ml_p"] = round(ml["p"], 3)
            result["ml_active"] = ml["active"]
            if ml["active"] and ml["p"] < ML_MIN_PROB:
                msg = (f"ML gate: learned P(profitable)={ml['p']:.0%} below "
                       f"{ML_MIN_PROB:.0%} (trained on {ml['n']} outcomes) — vetoed. {reasoning}")
                db.log_trade(ticker, signal, confidence, msg, price=price, status="VETOED_ML")
                result["vetoed"] = "ml"
                return result

    side = "BUY" if signal == "BUY" else "SELL"
    # confidence-scaled sizing: a 65% call risks less than a 95% call
    notional = MAX_ORDER_USDT * min(confidence, 1.0)
    # ML sizing: a trained model scales the bet by its predicted edge
    if ml and ml["active"]:
        notional *= max(0.4, min(1.0, 2 * ml["p"]))
    notional = round(notional, 2)
    if side == "BUY":
        notional = min(notional, MAX_OPEN_USDT - open_cost)  # never breach the cap

    if dry_run:
        qty = round(notional / price, 8) if side == "BUY" else (open_qty or None)
        db.log_trade(ticker, signal, confidence, reasoning,
                     price=price, qty=qty, side=side, status="DRY_RUN")
        alerts.notify(signal, ticker, confidence, reasoning, price, "DRY_RUN")
        result["action_taken"] = True
        result["dry_run"] = True
        result["notional"] = notional
        return result

    # safety latch: a real-money order requires BOTH live mode in .env AND the
    # per-run confirmation flag set by the dashboard. Never trips on testnet.
    if not BINANCE_TESTNET and not ALLOW_LIVE_TRADING:
        msg = "LIVE account without explicit confirmation — order blocked"
        db.log_trade(ticker, signal, confidence, reasoning, price=price, status="BLOCKED_LIVE")
        result["error"] = msg
        return result

    order_result = binance_client.place_market_order(ticker, side, notional, client)

    if order_result["ok"]:
        order = order_result["order"]
        db.log_trade(
            ticker, signal, confidence, reasoning,
            price=order_result["price"],
            qty=order_result["qty"],
            side=side,
            order_id=str(order.get("orderId")),
            status="FILLED",
        )
        alerts.notify(signal, ticker, confidence, reasoning, order_result["price"], "FILLED")
        result["action_taken"] = True
        result["order"] = order
    else:
        db.log_trade(
            ticker, signal, confidence, reasoning,
            price=price, status=f"ERROR: {order_result['error']}"
        )
        result["error"] = order_result["error"]

    return result
