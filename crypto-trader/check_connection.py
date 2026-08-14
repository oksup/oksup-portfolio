#!/usr/bin/env python3
"""Quick sanity check — run after filling in .env to verify connections.
Only Binance testnet keys are required; news comes from free RSS feeds."""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import sys


def check_binance():
    from src.config import BINANCE_TESTNET
    from src.trader.binance_client import get_client, get_price, get_usdt_balance
    label = "testnet" if BINANCE_TESTNET else "LIVE account"
    c = get_client()
    price = get_price("BTCUSDT", c)
    balance = get_usdt_balance(c)
    print(f"  Binance {label} OK | BTC/USDT: ${price:,.2f} | USDT balance: ${balance:,.2f}")


def check_news():
    from src.sentiment.scraper import fetch_rss
    headlines = fetch_rss("BTCUSDT", limit=3)
    if headlines:
        print(f"  News RSS OK | {len(headlines)} headlines | sample: \"{headlines[0][:60]}\"")
    else:
        print("  News RSS: no headlines returned (feeds may be slow — not fatal)")


checks = [("Binance", check_binance), ("News RSS", check_news)]
failed = False
for name, fn in checks:
    try:
        fn()
    except Exception as e:
        print(f"  {name} FAILED: {e}")
        failed = True

sys.exit(1 if failed else 0)
