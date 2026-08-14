from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9
from typing import Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException
from src.config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET


def get_client() -> Client:
    c = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=BINANCE_TESTNET)
    if BINANCE_TESTNET:
        c.API_URL = "https://testnet.binance.vision/api"
    return c


def get_price(ticker: str, client: Optional[Client] = None) -> float:
    c = client or get_client()
    return float(c.get_symbol_ticker(symbol=ticker)["price"])


def get_usdt_balance(client: Optional[Client] = None) -> float:
    c = client or get_client()
    balances = c.get_account()["balances"]
    usdt = next((b for b in balances if b["asset"] == "USDT"), None)
    return float(usdt["free"]) if usdt else 0.0


def place_market_order(ticker: str, side: str, usdt_amount: float, client: Optional[Client] = None) -> dict:
    """Places a market order sized by USDT amount. side = 'BUY' or 'SELL'."""
    c = client or get_client()
    price = get_price(ticker, c)
    info = c.get_symbol_info(ticker)
    step_size = next(
        f["stepSize"] for f in info["filters"] if f["filterType"] == "LOT_SIZE"
    )
    precision = len(step_size.rstrip("0").split(".")[-1]) if "." in step_size else 0
    qty = round(usdt_amount / price, precision)

    try:
        order = c.create_order(
            symbol=ticker,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=qty,
        )
        return {"ok": True, "order": order, "price": price, "qty": qty}
    except BinanceAPIException as e:
        return {"ok": False, "error": str(e), "price": price, "qty": qty}
