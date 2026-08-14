#!/usr/bin/env python3
"""
Simulation runner — runs 20 pipeline cycles using mock headlines and a
stubbed Binance price feed. No real API keys required.

Usage:
    python simulate.py
    python simulate.py --cycles 30
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import argparse
import random
import sqlite3
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# ── test data ──────────────────────────────────────────────────────────────────

BULLISH_HEADLINES = [
    "Bitcoin ETF sees record $800M inflow as institutional demand surges",
    "MicroStrategy adds 10,000 BTC to treasury at average $67,000",
    "Fed signals rate cut — crypto markets rally on dovish outlook",
    "BlackRock Bitcoin ETF becomes fastest to $10B AUM in history",
    "El Salvador BTC reserves up 40% as adoption spreads regionally",
    "Coinbase Q2 earnings beat expectations, BTC custody revenue triples",
    "JP Morgan upgrades Bitcoin price target to $150K by year-end",
    "On-chain data: long-term holders accumulating at 18-month high",
    "Bitcoin dominance hits 58% as altcoins rotate into BTC safety",
    "Lightning Network capacity hits all-time high, adoption accelerating",
]

BEARISH_HEADLINES = [
    "SEC charges major crypto exchange with unregistered securities fraud",
    "Bitcoin whale moves 8,000 BTC to exchanges — sell signal flashes",
    "China reiterates crypto mining ban, enforcement crackdown begins",
    "Mt. Gox trustee transfers $2.8B BTC to exchange wallets",
    "Bitcoin drops 12% in 24h as inflation data crushes rate-cut hopes",
    "Binance faces DOJ investigation over money laundering allegations",
    "Crypto fear & greed index hits 'extreme fear' at 14-year low",
    "Tether de-pegs briefly amid banking sector contagion fears",
    "Short sellers add $1.2B in BTC positions — bearish bets surge",
    "Regulatory crackdown: EU passes strict crypto KYC requirements",
]

NEUTRAL_HEADLINES = [
    "Bitcoin price consolidates near $68,000 as traders await catalyst",
    "Crypto market volume drops 30% over holiday weekend",
    "Ethereum completes minor network upgrade without incident",
    "Analyst: BTC likely range-bound between $65K–$72K near-term",
    "Mining difficulty adjusts down 2.1% after hash rate dip",
    "Crypto market cap holds steady at $2.4T amid macro uncertainty",
    "Bitcoin options expiry approaches — $3B in open interest",
    "On-chain metrics show mixed signals for short-term price action",
]

SCENARIOS = [
    {"label": "strong bull", "bullish": 8, "bearish": 1, "neutral": 1, "price_drift": +0.8},
    {"label": "moderate bull", "bullish": 5, "bearish": 2, "neutral": 3, "price_drift": +0.3},
    {"label": "neutral",      "bullish": 3, "bearish": 3, "neutral": 4, "price_drift": 0.0},
    {"label": "moderate bear","bullish": 2, "bearish": 5, "neutral": 3, "price_drift": -0.3},
    {"label": "strong bear",  "bullish": 1, "bearish": 8, "neutral": 1, "price_drift": -0.8},
]


def make_headlines(scenario: dict) -> list[str]:
    pool = (
        random.sample(BULLISH_HEADLINES, min(scenario["bullish"], len(BULLISH_HEADLINES))) +
        random.sample(BEARISH_HEADLINES, min(scenario["bearish"], len(BEARISH_HEADLINES))) +
        random.sample(NEUTRAL_HEADLINES, min(scenario["neutral"], len(NEUTRAL_HEADLINES)))
    )
    random.shuffle(pool)
    return pool


def mock_analyze(headlines: list[str], ticker: str) -> dict:
    bull = sum(1 for h in headlines if h in BULLISH_HEADLINES)
    bear = sum(1 for h in headlines if h in BEARISH_HEADLINES)
    total = bull + bear or 1
    bull_ratio = bull / total

    if bull_ratio >= 0.65:
        signal, confidence = "BUY", round(0.60 + bull_ratio * 0.35, 2)
        reasoning = f"{bull} bullish vs {bear} bearish signals indicate upward momentum"
    elif bull_ratio <= 0.35:
        signal, confidence = "SELL", round(0.60 + (1 - bull_ratio) * 0.35, 2)
        reasoning = f"{bear} bearish vs {bull} bullish signals indicate downward pressure"
    else:
        signal, confidence = "HOLD", round(0.40 + abs(bull_ratio - 0.5) * 0.3, 2)
        reasoning = f"Mixed sentiment ({bull} bullish, {bear} bearish) — insufficient edge"

    classified = [
        {"headline": h, "sentiment": "BULLISH" if h in BULLISH_HEADLINES else ("BEARISH" if h in BEARISH_HEADLINES else "NEUTRAL")}
        for h in headlines
    ]
    return {"signal": signal, "confidence": confidence, "reasoning": reasoning, "classified_headlines": classified}


# ── simulation ──────────────────────────────────────────────────────────────────

def run_simulation(cycles: int = 20, append: bool = False, ticker: str = None):
    from src.config import DB_PATH, SIGNAL_CONFIDENCE_THRESHOLD, MAX_ORDER_USDT, TICKER
    from src.trader.db import init_db, log_trade
    ticker = ticker or TICKER

    # wipe and reinit DB for clean sim run (unless appending to the existing log)
    if not append and os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            # file deletion can be blocked (sandbox/lock) — clear rows instead
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM trades")
            con.commit()
            con.close()
    init_db()

    # anchor the sim near the asset's real price when reachable
    try:
        from src import market
        base_price = market.get_price(ticker) or 68_420.0
    except Exception:
        base_price = 68_420.0
    sim_start = datetime.now(timezone.utc) - timedelta(hours=cycles * 0.25)

    print(f"\n{'═'*70}")
    print(f"  SIMULATION — {ticker} — {cycles} cycles @ 15-min intervals")
    print(f"  Starting price: ${base_price:,.2f} | Threshold: {SIGNAL_CONFIDENCE_THRESHOLD:.0%}")
    print(f"{'═'*70}")
    print(f"  {'#':<4} {'Scenario':<15} {'Signal':<6} {'Conf':>5}  {'Price':>10}  Status")
    print(f"  {'─'*62}")

    G, R, Y, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"

    price = base_price
    results = []

    for i in range(cycles):
        scenario = random.choice(SCENARIOS)
        headlines = make_headlines(scenario)
        analysis = mock_analyze(headlines, ticker)

        # drift price based on scenario
        price *= 1 + (scenario["price_drift"] / 100) + random.uniform(-0.002, 0.002)

        signal = analysis["signal"]
        confidence = analysis["confidence"]
        reasoning = analysis["reasoning"]
        ts = (sim_start + timedelta(minutes=15 * i)).isoformat()

        if signal == "HOLD" or confidence < SIGNAL_CONFIDENCE_THRESHOLD:
            status = "SKIPPED"
        else:
            status = "DRY_RUN"

        # write directly with simulated timestamp
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO trades (ts, ticker, signal, confidence, reasoning, price, side, status) VALUES (?,?,?,?,?,?,?,?)",
            (ts, ticker, signal, confidence, reasoning, round(price, 2),
             signal if signal != "HOLD" else None, status),
        )
        con.commit()
        con.close()

        color = G if signal == "BUY" else (R if signal == "SELL" else Y)
        results.append({"signal": signal, "confidence": confidence, "status": status})
        print(f"  {i+1:<4} {scenario['label']:<15} {color}{signal:<6}{RESET} {confidence:.0%}  ${price:>9,.2f}  {status}")

    # summary
    buys   = sum(1 for r in results if r["signal"] == "BUY")
    sells  = sum(1 for r in results if r["signal"] == "SELL")
    holds  = sum(1 for r in results if r["signal"] == "HOLD")
    acted  = sum(1 for r in results if r["status"] == "DRY_RUN")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")
    avg_conf = sum(r["confidence"] for r in results) / len(results)

    print(f"\n{'═'*70}")
    print(f"  Results: {G}BUY {buys}{RESET}  {R}SELL {sells}{RESET}  {Y}HOLD {holds}{RESET}")
    print(f"  Acted on: {acted}  |  Skipped (below threshold): {skipped}")
    print(f"  Avg confidence: {avg_conf:.0%}  |  Final price: ${price:,.2f}")
    print(f"  Trade log written → {DB_PATH}")
    print(f"{'═'*70}")
    print(f"\n  Run  python pnl.py  or  python show_trades.py  to inspect results.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=20)
    parser.add_argument("--append", action="store_true",
                        help="Append to the existing trade log instead of wiping it")
    parser.add_argument("--ticker", default=None, help="Asset to simulate (defaults to TICKER from .env)")
    args = parser.parse_args()
    run_simulation(args.cycles, append=args.append, ticker=args.ticker)
