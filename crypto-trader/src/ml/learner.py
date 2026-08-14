"""
Online learning layer — the system learns from its own track record.

A pure-Python online logistic regression (no heavy ML deps, Python 3.9 safe)
that predicts P(this signal will be profitable) from features available at
decision time. It trains incrementally: every run, signals whose outcome has
matured (price known ~4h later) become new labeled examples, and the weights
update by stochastic gradient descent.

Learning persists in data/model.json — it survives restarts, dashboard
sessions, and even trade-log wipes, so everything the system has learned
carries forward to future trading.

How it's used by the executor:
- assess() scores a new signal; once the model has seen >= MIN_SAMPLES
  outcomes it becomes ACTIVE: low-probability signals are vetoed
  (VETOED_ML) and order size is scaled by the predicted probability.
- Before that it stays in observation mode (no vetoes) — cold-start safety.

Features (recomputed from the trade log, so no schema change):
  confidence, signal direction, trend (price vs mean of recent logged
  prices, same asset), recent volatility, and a bias term.
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import json
import math
import os
from datetime import datetime

MODEL_PATH = "data/model.json"
LEARNING_RATE = 0.08
EPOCHS = 8                # passes over each new batch (shuffled) — single-pass SGD is too order-sensitive
MIN_SAMPLES = 20          # model is advisory-only until it has this many outcomes
HORIZON_S = 4 * 3600      # outcome = price move 4h after the signal
SLACK_FRACTION = 0.75     # accept the first price in [h, h*(1+slack)]
MIN_MOVE = 0.002          # move must beat ~fees (0.2%) to count as a win
FEATURES = ["bias", "confidence", "is_buy", "trend_up", "volatility"]


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def _epoch(ts: str) -> float:
    return datetime.fromisoformat(ts).timestamp()


def _load():
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH) as f:
                m = json.load(f)
            if set(m.get("w", {})) == set(FEATURES):
                return m
        except Exception:
            pass
    return {"w": {f: 0.0 for f in FEATURES}, "trained": [], "history": []}


def _save(m: dict):
    os.makedirs(os.path.dirname(MODEL_PATH) or ".", exist_ok=True)
    with open(MODEL_PATH, "w") as f:
        json.dump(m, f)


def _features(confidence: float, signal: str, price: float, prior_prices: list) -> dict:
    """Decision-time features from the asset's own logged price history."""
    f = {"bias": 1.0, "confidence": float(confidence),
         "is_buy": 1.0 if signal == "BUY" else 0.0}
    recent = [p for p in prior_prices if p][-12:]
    if len(recent) >= 5:
        sma = sum(recent) / len(recent)
        f["trend_up"] = 1.0 if price >= sma else 0.0
        rets = [abs(recent[i] / recent[i - 1] - 1) for i in range(1, len(recent))]
        f["volatility"] = min(sum(rets) / len(rets) * 100, 3.0) / 3.0
    else:
        f["trend_up"] = 0.5     # unknown trend — neutral
        f["volatility"] = 0.3
    return f


def _predict(m: dict, f: dict) -> float:
    return _sigmoid(sum(m["w"][k] * f[k] for k in FEATURES))


def update_model(trades: list) -> dict:
    """Train on every signal whose outcome has matured and isn't trained yet.
    Returns {"new": n, "total": n, "recent_accuracy": float|None}."""
    m = _load()
    trained = set(m["trained"])

    # per-asset price series from the log
    by_ticker = {}
    for t in sorted((t for t in trades if t.get("price")), key=lambda t: t["ts"]):
        by_ticker.setdefault(t["ticker"], []).append((_epoch(t["ts"]), float(t["price"])))

    # collect the batch of newly matured, labeled examples first
    batch = []
    for t in sorted(trades, key=lambda t: t["ts"]):
        if t["signal"] not in ("BUY", "SELL") or not t.get("price"):
            continue
        key = f"{t['ts']}|{t['ticker']}"
        if key in trained:
            continue
        series = by_ticker.get(t["ticker"], [])
        t0, p0 = _epoch(t["ts"]), float(t["price"])
        future = next((p for e, p in series
                       if t0 + HORIZON_S <= e <= t0 + HORIZON_S * (1 + SLACK_FRACTION)), None)
        if future is None:
            continue  # not matured yet — try again next run
        move = future / p0 - 1
        label = 1.0 if ((t["signal"] == "BUY" and move > MIN_MOVE) or
                        (t["signal"] == "SELL" and move < -MIN_MOVE)) else 0.0
        prior = [p for e, p in series if e < t0]
        f = _features(t["confidence"], t["signal"], p0, prior)
        # record the model's pre-training prediction for honest accuracy tracking
        m["history"].append({"label": label, "p": round(_predict(m, f), 4)})
        batch.append((key, f, label))
        trained.add(key)

    # multi-epoch shuffled SGD — order-robust on small batches
    if batch:
        import random
        rng = random.Random(42)
        for _ in range(EPOCHS):
            rng.shuffle(batch)
            for _key, f, label in batch:
                p = _predict(m, f)
                for k in FEATURES:
                    m["w"][k] += LEARNING_RATE * (label - p) * f[k]

    new = len(batch)
    m["trained"] = list(trained)
    m["history"] = m["history"][-200:]
    if new:
        _save(m)

    recent = m["history"][-50:]
    acc = (sum(1 for h in recent if (h["p"] >= 0.5) == (h["label"] == 1.0)) / len(recent)
           if recent else None)
    return {"new": new, "total": len(trained), "recent_accuracy": acc}


def assess(trades: list, ticker: str, signal: str, confidence: float, price: float) -> dict:
    """Score a prospective signal. active=False means observation mode only."""
    m = _load()
    prior = [float(t["price"]) for t in sorted(trades, key=lambda t: t["ts"])
             if t["ticker"] == ticker and t.get("price")]
    f = _features(confidence, signal, price, prior)
    return {"p": _predict(m, f), "active": len(m["trained"]) >= MIN_SAMPLES,
            "n": len(m["trained"]), "features": f}


def stats() -> dict:
    """Snapshot for the dashboard."""
    m = _load()
    recent = m["history"][-50:]
    acc = (sum(1 for h in recent if (h["p"] >= 0.5) == (h["label"] == 1.0)) / len(recent)
           if recent else None)
    wins = sum(1 for h in m["history"] if h["label"] == 1.0)
    return {
        "total": len(m["trained"]),
        "active": len(m["trained"]) >= MIN_SAMPLES,
        "min_samples": MIN_SAMPLES,
        "recent_accuracy": acc,
        "base_rate": (wins / len(m["history"])) if m["history"] else None,
        "weights": dict(m["w"]),
    }


def reset():
    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)
