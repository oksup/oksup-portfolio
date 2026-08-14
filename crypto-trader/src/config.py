"""All env config.

Values are read from .env at import time. The dashboard purges src.* modules
before each in-process run, so .env edits (account mode, ticker, threshold)
take effect on the very next run — no restart needed.
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import os
from dotenv import load_dotenv

load_dotenv(override=True)

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

# Safety latch: real (non-testnet) orders are refused unless this is true.
# The dashboard sets it per-run after an explicit confirmation checkbox —
# do NOT put it in .env, that would defeat the protection.
ALLOW_LIVE_TRADING = os.getenv("ALLOW_LIVE_TRADING", "false").lower() == "true"

TICKER = os.getenv("TICKER", "BTCUSDT")
SIGNAL_CONFIDENCE_THRESHOLD = float(os.getenv("SIGNAL_CONFIDENCE_THRESHOLD", "0.65"))
MAX_ORDER_USDT = float(os.getenv("MAX_ORDER_USDT", "100"))

# ── risk management ──
MAX_OPEN_USDT = float(os.getenv("MAX_OPEN_USDT", "300"))      # exposure cap across open position
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "2.5"))      # force-sell if position down this % (0 = off)
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "4"))    # force-sell if position up this % (0 = off)
# 4%TP / 2.5%SL ≈ 1.6:1 reward/risk — profitable from ~42% win rate after fees
TREND_FILTER = os.getenv("TREND_FILTER", "true").lower() == "true"  # only BUY above the 20-period SMA
# raise the confidence bar for a side while its rolling 4h scorecard accuracy is under 50%
ADAPTIVE_THRESHOLD = os.getenv("ADAPTIVE_THRESHOLD", "true").lower() == "true"
FEE_RATE = float(os.getenv("FEE_RATE", "0.001"))              # Binance taker fee, used in paper PnL

# ── machine learning gate ──
ML_GATE = os.getenv("ML_GATE", "true").lower() == "true"      # let the learner veto/size trades once trained
ML_MIN_PROB = float(os.getenv("ML_MIN_PROB", "0.35"))         # veto signals the model scores below this

DB_PATH = "data/trades.db"
LOG_PATH = "logs/trader.log"
