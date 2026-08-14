"""
Asset registry — every tradeable symbol the system knows about.

Crypto assets trade on Binance (testnet/live). Stocks get prices and news
from free keyless Yahoo/Google endpoints and are PAPER-ONLY: signals are
logged and tracked in the paper portfolio, but no real orders exist for
them (Binance doesn't trade Apple).
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

ASSETS = {
    "BTCUSDT": {"name": "Bitcoin",  "kind": "crypto", "icon": "₿",
                "yahoo": "BTC-USD", "terms": ["bitcoin", "btc"]},
    "ETHUSDT": {"name": "Ethereum", "kind": "crypto", "icon": "Ξ",
                "yahoo": "ETH-USD", "terms": ["ethereum", "eth", "ether"]},
    "SOLUSDT": {"name": "Solana",   "kind": "crypto", "icon": "◎",
                "yahoo": "SOL-USD", "terms": ["solana", "sol"]},
    "AAPL":  {"name": "Apple",             "kind": "stock", "icon": "🍎",
              "yahoo": "AAPL",  "terms": ["apple", "aapl", "iphone", "tim cook", "app store"]},
    "GOOGL": {"name": "Alphabet (Google)", "kind": "stock", "icon": "🔍",
              "yahoo": "GOOGL", "terms": ["google", "alphabet", "googl", "android", "youtube"]},
    "MSFT":  {"name": "Microsoft",         "kind": "stock", "icon": "🪟",
              "yahoo": "MSFT",  "terms": ["microsoft", "msft", "azure", "windows", "copilot"]},
    "TSLA":  {"name": "Tesla",             "kind": "stock", "icon": "🚗",
              "yahoo": "TSLA",  "terms": ["tesla", "tsla", "elon musk", "cybertruck"]},
}


def get_asset(symbol: str) -> dict:
    if symbol in ASSETS:
        return {"symbol": symbol, **ASSETS[symbol]}
    # unknown symbol: infer kind so custom tickers still mostly work
    kind = "crypto" if symbol.upper().endswith(("USDT", "USDC", "BUSD")) else "stock"
    base = symbol[:-4] if kind == "crypto" else symbol
    return {"symbol": symbol, "name": symbol, "kind": kind, "icon": "•",
            "yahoo": f"{base}-USD" if kind == "crypto" else symbol,
            "terms": [base.lower()]}


def is_crypto(symbol: str) -> bool:
    return get_asset(symbol)["kind"] == "crypto"
