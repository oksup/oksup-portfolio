"""
Smoke tests — no network, no API keys. Run: python3 -m pytest tests/ -q
Guards the bug classes that have actually bitten this project:
runtime annotation errors on Python 3.9, broken imports after refactors,
and analyzer/portfolio math regressions.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ENTRY_POINTS = [
    "main.py", "simulate.py", "fetch_headlines.py",
    "execute_signal.py", "check_connection.py", "dashboard.py", "pnl.py", "show_trades.py",
]


def test_all_entry_points_have_future_annotations_or_no_unions():
    """PEP 604 unions (`X | None`) crash at runtime on Python 3.9 unless
    `from __future__ import annotations` is present. This is the bug that
    twice broke the project — fail fast if it regresses."""
    for f in ENTRY_POINTS + [str(p.relative_to(ROOT)) for p in (ROOT / "src").rglob("*.py")]:
        src = (ROOT / f).read_text()
        has_union = " | None" in src or "| None:" in src
        has_future = "from __future__ import annotations" in src
        has_optional = "Optional[" in src
        assert not (has_union and not has_future), (
            f"{f} uses `X | None` without `from __future__ import annotations` — crashes on Python 3.9"
        )


def test_modules_import():
    import src.config
    import src.sentiment.scraper
    import src.sentiment.analyzer
    import src.trader.db
    import src.trader.portfolio
    import src.alerts


def test_analyzer_signals():
    from src.sentiment.analyzer import analyze
    bull = analyze(["Bitcoin ETF sees record inflow as institutional buying surges"] * 5)
    assert bull["signal"] == "BUY" and bull["confidence"] > 0.5
    bear = analyze(["SEC charges exchange with fraud amid crackdown and selloff"] * 5)
    assert bear["signal"] == "SELL" and bear["confidence"] > 0.5
    empty = analyze([])
    assert empty["signal"] == "HOLD" and empty["confidence"] == 0.0


def test_portfolio_replay_profit_and_loss():
    from src.trader.portfolio import replay
    # buy at 100, sell at 110 → +10% on the position
    win = replay([
        {"ts": "2026-01-01T00:00", "signal": "BUY",  "status": "DRY_RUN", "price": 100.0, "qty": None},
        {"ts": "2026-01-01T01:00", "signal": "SELL", "status": "DRY_RUN", "price": 110.0, "qty": None},
    ], starting_usdt=1000.0)
    assert win["closed"] == 1 and win["wins"] == 1 and win["win_rate"] == 1.0
    assert round(win["total_pnl"], 6) > 0
    # buy at 100, sell at 90 → loss
    loss = replay([
        {"ts": "2026-01-01T00:00", "signal": "BUY",  "status": "DRY_RUN", "price": 100.0, "qty": None},
        {"ts": "2026-01-01T01:00", "signal": "SELL", "status": "DRY_RUN", "price": 90.0,  "qty": None},
    ], starting_usdt=1000.0)
    assert loss["total_pnl"] < 0 and loss["win_rate"] == 0.0
    # skipped/hold rows are ignored
    flat = replay([
        {"ts": "2026-01-01T00:00", "signal": "HOLD", "status": "SKIPPED", "price": 100.0, "qty": None},
    ])
    assert flat["total_pnl"] == 0 and flat["closed"] == 0


def test_analyzer_weighting():
    """Fresh, relevant, high-trust headlines must outweigh stale Reddit noise."""
    import time
    from src.sentiment.analyzer import analyze
    now = time.time()
    headlines = (
        # 3 fresh CoinDesk bullish Bitcoin headlines — heavy weight
        [{"title": "Bitcoin ETF inflow surges to record as institutional buying accelerates",
          "source": "coindesk", "published": now - 600}] * 3 +
        # 4 day-old Reddit bearish posts not about Bitcoin — light weight
        [{"title": "Dogecoin crash deepens amid massive selloff and liquidations",
          "source": "reddit", "published": now - 86400}] * 4
    )
    res = analyze(headlines, "BTCUSDT")
    assert res["signal"] == "BUY", f"weighting failed: {res['reasoning']}"
    # plain strings still work (back-compat)
    res2 = analyze(["Bitcoin rally continues as inflows surge"] * 3, "BTCUSDT")
    assert res2["signal"] == "BUY"


def test_portfolio_fees(monkeypatch):
    """Paper PnL must charge the taker fee on both sides of a round trip."""
    from src.trader import portfolio
    from src.trader.portfolio import replay
    monkeypatch.setattr(portfolio, "MAX_ORDER_USDT", 100.0)
    monkeypatch.setattr(portfolio, "FEE_RATE", 0.001)
    win = replay([
        {"ts": "2026-01-01T00:00", "signal": "BUY",  "status": "DRY_RUN", "price": 100.0, "qty": None},
        {"ts": "2026-01-01T01:00", "signal": "SELL", "status": "DRY_RUN", "price": 110.0, "qty": None},
    ], starting_usdt=1000.0)
    # gross +10% on $100 = $10; with 0.1% fees both ways it must land just below
    assert 9.0 < win["total_pnl"] < 10.0, f"fees not applied: pnl={win['total_pnl']}"


def test_scorecard():
    from src.trader.scorecard import evaluate
    trades = [
        {"ts": "2026-01-01T00:00:00", "signal": "BUY",  "price": 100.0, "status": "DRY_RUN"},
        {"ts": "2026-01-01T01:00:00", "signal": "SELL", "price": 105.0, "status": "DRY_RUN"},
        {"ts": "2026-01-01T02:00:00", "signal": "HOLD", "price": 101.0, "status": "SKIPPED"},
    ]
    sc = evaluate(trades)
    h1 = sc["horizons"]["1h"]
    assert h1["BUY"]["total"] == 1 and h1["BUY"]["correct"] == 1      # 100 → 105 ✓
    assert h1["SELL"]["total"] == 1 and h1["SELL"]["correct"] == 1    # 105 → 101 ✓
    assert h1["overall_accuracy"] == 1.0


def _quiet_executor(monkeypatch, price=100.0, open_pos=(0.0, 0.0), sma=None):
    """Executor with all I/O stubbed: returns (executor, orders_placed, log_rows)."""
    from src.trader import executor
    monkeypatch.setattr(executor.binance_client, "get_client", lambda: object())
    monkeypatch.setattr(executor.binance_client, "get_price", lambda t, c=None: price)
    monkeypatch.setattr(executor.market, "get_price", lambda s: price)
    monkeypatch.setattr(executor, "_open_position", lambda t, tr=None: open_pos)
    monkeypatch.setattr(executor, "_sma", lambda *a, **k: sma)
    monkeypatch.setattr(executor.alerts, "notify", lambda *a, **k: None)
    monkeypatch.setattr(executor, "SIGNAL_CONFIDENCE_THRESHOLD", 0.5)
    monkeypatch.setattr(executor.db, "all_trades", lambda: [])
    monkeypatch.setattr(executor.learner, "update_model",
                        lambda t: {"new": 0, "total": 0, "recent_accuracy": None})
    monkeypatch.setattr(executor.learner, "assess",
                        lambda *a, **k: {"p": 0.6, "active": False, "n": 0, "features": {}})
    orders, logged = [], []
    monkeypatch.setattr(executor.binance_client, "place_market_order",
                        lambda *a, **k: orders.append(a) or {"ok": True, "order": {"orderId": 1},
                                                             "price": price, "qty": 0.001})
    monkeypatch.setattr(executor.db, "log_trade",
                        lambda *a, **k: logged.append({"args": a, **k}))
    return executor, orders, logged


def test_trend_filter_vetoes_buy_below_sma(monkeypatch):
    ex, orders, logged = _quiet_executor(monkeypatch, price=100.0, sma=105.0)
    monkeypatch.setattr(ex, "TREND_FILTER", True)
    res = ex.execute({"signal": "BUY", "confidence": 0.9, "reasoning": "t"}, "BTCUSDT", dry_run=True)
    assert res.get("vetoed") == "trend" and not res["action_taken"]
    assert logged[-1]["status"] == "VETOED_TREND"


def test_exposure_cap_vetoes_buy(monkeypatch):
    ex, orders, logged = _quiet_executor(monkeypatch, price=100.0, open_pos=(3.5, 350.0))
    monkeypatch.setattr(ex, "MAX_OPEN_USDT", 300.0)
    monkeypatch.setattr(ex, "TREND_FILTER", False)
    res = ex.execute({"signal": "BUY", "confidence": 0.9, "reasoning": "t"}, "BTCUSDT", dry_run=True)
    assert res.get("vetoed") == "exposure" and not res["action_taken"]
    assert logged[-1]["status"] == "VETOED_RISK"


def test_take_profit_forces_sell(monkeypatch):
    # position: 1 unit at $100 cost basis; price now $105 = +5%, target 4% → bank it
    ex, orders, logged = _quiet_executor(monkeypatch, price=105.0, open_pos=(1.0, 100.0))
    monkeypatch.setattr(ex, "TAKE_PROFIT_PCT", 4.0)
    res = ex.execute({"signal": "HOLD", "confidence": 0.1, "reasoning": "nothing"}, "BTCUSDT", dry_run=True)
    assert res.get("take_profit") is True and res["signal"] == "SELL"
    assert res["action_taken"] and logged[-1]["status"] == "DRY_RUN"
    assert "TAKE-PROFIT" in logged[-1]["args"][3]


def test_adaptive_threshold_raises_bar_for_losing_side(monkeypatch):
    """While BUY calls score <50% on the 4h scorecard, a BUY that clears the
    base threshold but not the raised one must be SKIPPED."""
    from datetime import datetime, timedelta
    ex, orders, logged = _quiet_executor(monkeypatch, price=100.0)
    monkeypatch.setattr(ex, "ADAPTIVE_THRESHOLD", True)
    monkeypatch.setattr(ex, "TREND_FILTER", False)
    # 12 BUY calls, every one followed 4h later by a lower price → 0% accuracy
    t0 = datetime(2026, 1, 1)
    hist = []
    for i in range(12):
        hist.append({"ts": (t0 + timedelta(hours=5 * i)).isoformat(), "ticker": "BTCUSDT",
                     "signal": "BUY", "confidence": 0.9, "price": 100.0, "status": "DRY_RUN"})
        hist.append({"ts": (t0 + timedelta(hours=5 * i + 4)).isoformat(), "ticker": "BTCUSDT",
                     "signal": "HOLD", "confidence": 0.3, "price": 95.0, "status": "SKIPPED"})
    monkeypatch.setattr(ex.db, "all_trades", lambda: hist)
    # base threshold 0.5 (set in _quiet_executor) → raised to 0.65; 0.6 must now be skipped
    res = ex.execute({"signal": "BUY", "confidence": 0.60, "reasoning": "t"}, "BTCUSDT", dry_run=True)
    assert not res["action_taken"] and res.get("adaptive_skip") is True
    assert logged[-1]["status"] == "SKIPPED" and "Adaptive threshold" in logged[-1]["args"][3]
    # SELL side is unaffected — 0.6 still trades
    res2 = ex.execute({"signal": "SELL", "confidence": 0.60, "reasoning": "t"}, "BTCUSDT", dry_run=True)
    assert res2["action_taken"]


def test_stop_loss_forces_sell(monkeypatch):
    # position: 1 BTC at $100 cost basis; price now $90 = -10%, limit 5% → forced SELL
    ex, orders, logged = _quiet_executor(monkeypatch, price=90.0, open_pos=(1.0, 100.0))
    monkeypatch.setattr(ex, "STOP_LOSS_PCT", 5.0)
    res = ex.execute({"signal": "HOLD", "confidence": 0.1, "reasoning": "nothing"}, "BTCUSDT", dry_run=True)
    assert res.get("stop_loss") is True and res["signal"] == "SELL"
    assert res["action_taken"] and logged[-1]["status"] == "DRY_RUN"
    assert "STOP-LOSS" in logged[-1]["args"][3]


def test_asset_registry():
    from src.assets import get_asset, is_crypto
    assert is_crypto("BTCUSDT") and is_crypto("ETHUSDT")
    assert not is_crypto("AAPL") and not is_crypto("GOOGL")
    assert get_asset("AAPL")["kind"] == "stock"
    assert get_asset("DOGEUSDT")["kind"] == "crypto"   # unknown symbol, kind inferred
    assert get_asset("NVDA")["kind"] == "stock"


def test_stock_is_paper_only(monkeypatch):
    """A stock order with dry-run OFF must still never touch Binance."""
    ex, orders, logged = _quiet_executor(monkeypatch, price=200.0)
    monkeypatch.setattr(ex, "TREND_FILTER", False)
    res = ex.execute({"signal": "BUY", "confidence": 0.9, "reasoning": "t"}, "AAPL", dry_run=False)
    assert res["paper_only"] is True and res["dry_run"] is True
    assert orders == [], "no real order may exist for a stock"
    assert logged[-1]["status"] == "DRY_RUN"


def test_ml_gate_vetoes_low_probability(monkeypatch):
    ex, orders, logged = _quiet_executor(monkeypatch, price=100.0)
    monkeypatch.setattr(ex, "ML_GATE", True)
    monkeypatch.setattr(ex, "ML_MIN_PROB", 0.35)
    monkeypatch.setattr(ex, "TREND_FILTER", False)
    monkeypatch.setattr(ex.learner, "assess",
                        lambda *a, **k: {"p": 0.10, "active": True, "n": 50, "features": {}})
    res = ex.execute({"signal": "BUY", "confidence": 0.9, "reasoning": "t"}, "BTCUSDT", dry_run=True)
    assert res.get("vetoed") == "ml" and not res["action_taken"]
    assert logged[-1]["status"] == "VETOED_ML"


def test_learner_learns_and_persists(tmp_path, monkeypatch):
    """The model must learn from outcomes (uptrend BUYs win, downtrend BUYs lose),
    score new signals accordingly, and persist across reloads."""
    from datetime import datetime, timedelta
    from src.ml import learner
    monkeypatch.setattr(learner, "MODEL_PATH", str(tmp_path / "model.json"))

    # 40 hourly BUY signals: 20 in a +1%/h uptrend (wins), 20 in a -1%/h downtrend (losses)
    t0 = datetime(2026, 1, 1)
    rows, price = [], 100.0
    for i in range(40):
        price *= 1.01 if i < 20 else 0.99
        rows.append({"ts": (t0 + timedelta(hours=i)).isoformat(), "ticker": "BTCUSDT",
                     "signal": "BUY", "confidence": 0.8, "price": round(price, 4),
                     "status": "DRY_RUN"})

    stats = learner.update_model(rows)
    assert stats["new"] >= 20, "should have trained on the matured signals"
    assert stats["total"] >= learner.MIN_SAMPLES

    # uptrend context must score higher than downtrend context
    up = learner.assess(rows[:20], "BTCUSDT", "BUY", 0.8, rows[19]["price"] * 1.01)
    down = learner.assess(rows[20:], "BTCUSDT", "BUY", 0.8, rows[-1]["price"] * 0.99)
    assert up["active"] and up["p"] > down["p"], (
        f"model failed to learn trend matters: up={up['p']:.3f} down={down['p']:.3f}")

    # persistence: a fresh load sees the same training count, and retraining
    # the same rows adds nothing (already learned)
    again = learner.update_model(rows)
    assert again["new"] == 0 and again["total"] == stats["total"]


def test_live_orders_blocked_without_confirmation(monkeypatch):
    """A real-money order needs BOTH live mode and the per-run confirmation
    latch. Without the latch, the order must be blocked — never sent."""
    from src.trader import executor

    monkeypatch.setattr(executor, "BINANCE_TESTNET", False)
    monkeypatch.setattr(executor, "ALLOW_LIVE_TRADING", False)
    monkeypatch.setattr(executor, "SIGNAL_CONFIDENCE_THRESHOLD", 0.5)
    monkeypatch.setattr(executor, "_open_position", lambda t, tr=None: (0.0, 0.0))
    monkeypatch.setattr(executor, "_sma", lambda *a, **k: None)
    monkeypatch.setattr(executor.db, "all_trades", lambda: [])
    monkeypatch.setattr(executor.learner, "update_model",
                        lambda t: {"new": 0, "total": 0, "recent_accuracy": None})
    monkeypatch.setattr(executor.learner, "assess",
                        lambda *a, **k: {"p": 0.6, "active": False, "n": 0, "features": {}})
    monkeypatch.setattr(executor.binance_client, "get_client", lambda: object())
    monkeypatch.setattr(executor.binance_client, "get_price", lambda t, c=None: 50_000.0)
    orders = []
    monkeypatch.setattr(executor.binance_client, "place_market_order",
                        lambda *a, **k: orders.append(a))
    logged = []
    monkeypatch.setattr(executor.db, "log_trade",
                        lambda *a, **k: logged.append(k.get("status")))

    res = executor.execute({"signal": "BUY", "confidence": 0.99, "reasoning": "t"},
                           "BTCUSDT", dry_run=False)
    assert orders == [], "order must NOT be placed without the live-trading latch"
    assert "blocked" in res.get("error", "").lower()
    assert "BLOCKED_LIVE" in logged

    # with the latch set, the order goes through
    monkeypatch.setattr(executor, "ALLOW_LIVE_TRADING", True)
    monkeypatch.setattr(executor.binance_client, "place_market_order",
                        lambda *a, **k: {"ok": True, "order": {"orderId": 1}, "price": 50_000.0, "qty": 0.002})
    monkeypatch.setattr(executor.alerts, "notify", lambda *a, **k: None)
    res = executor.execute({"signal": "BUY", "confidence": 0.99, "reasoning": "t"},
                           "BTCUSDT", dry_run=False)
    assert res["action_taken"] is True


def test_execute_signal_skips_below_threshold(tmp_path):
    """execute_signal.py with low confidence must log SKIPPED and exit 0 — no keys needed."""
    env = dict(os.environ)
    env.pop("BINANCE_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "execute_signal.py", "--signal", "BUY", "--confidence", "0.10",
         "--reasoning", "smoke test low confidence", "--dry-run"],
        capture_output=True, text=True, cwd=str(ROOT), env=env,
    )
    assert r.returncode == 0, r.stderr
    assert "SKIPPED" in r.stdout
