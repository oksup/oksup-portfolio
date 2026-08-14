"""
Unified market-data provider — free, keyless.

- Crypto: Binance public REST (ticker/price, klines)
- Stocks: Yahoo Finance v8 chart API (price, historical closes)

Everything degrades to None on failure so callers can stand aside gracefully.
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import requests

from src.assets import get_asset, is_crypto

_UA = {"User-Agent": "Mozilla/5.0 (crypto-trader paper-bot)"}


def get_price(symbol: str):
    """Latest price for any registered asset. None on failure."""
    try:
        if is_crypto(symbol):
            r = requests.get("https://api.binance.com/api/v3/ticker/price",
                             params={"symbol": symbol}, timeout=10)
            r.raise_for_status()
            return float(r.json()["price"])
        return _yahoo_price(get_asset(symbol)["yahoo"])
    except Exception:
        return None


def _yahoo_price(yahoo_symbol: str):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}",
                     params={"range": "1d", "interval": "1m"}, headers=_UA, timeout=10)
    r.raise_for_status()
    meta = r.json()["chart"]["result"][0]["meta"]
    return float(meta["regularMarketPrice"])


def get_closes(symbol: str, limit: int = 20, interval: str = "15m"):
    """Recent closing prices, oldest first. None on failure."""
    try:
        if is_crypto(symbol):
            r = requests.get("https://api.binance.com/api/v3/klines",
                             params={"symbol": symbol, "interval": interval, "limit": limit},
                             timeout=10)
            r.raise_for_status()
            return [float(k[4]) for k in r.json()]
        yahoo = get_asset(symbol)["yahoo"]
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo}",
                         params={"range": "5d", "interval": interval}, headers=_UA, timeout=10)
        r.raise_for_status()
        closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        return closes[-limit:] if closes else None
    except Exception:
        return None


def get_sma(symbol: str, periods: int = 20, interval: str = "15m"):
    """Simple moving average; None when data is unavailable."""
    closes = get_closes(symbol, limit=periods, interval=interval)
    return (sum(closes) / len(closes)) if closes else None
