"""
Free headline scraper — RSS feeds (no API key needed) + Reddit.
Crypto: CoinDesk, CoinTelegraph, Decrypt, Bitcoin Magazine, Reddit r/CryptoCurrency
Stocks: Yahoo Finance RSS + Google News RSS

All feeds are fetched IN PARALLEL with hard timeouts — a slow or dead feed
costs at most FETCH_TIMEOUT seconds, never hangs the pipeline.
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9
import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests

from src.config import TICKER

CURRENCY_MAP = {"BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana"}
TICKER_SYMBOL = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL"}

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
]

FETCH_TIMEOUT = 8
_UA = {"User-Agent": "Mozilla/5.0 (crypto-trader paper-bot)"}


def _feed_source(url: str) -> str:
    for name in ("coindesk", "cointelegraph", "decrypt", "bitcoinmagazine"):
        if name in url:
            return name
    return "rss"


def _parse_feed(url: str, source: str) -> list[dict]:
    """Fetch one RSS feed with a hard timeout (feedparser alone has none)."""
    try:
        r = requests.get(url, headers=_UA, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        out = []
        for entry in feed.entries:
            title = entry.get("title", "")
            if not title:
                continue
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            out.append({
                "title": title,
                "source": source,
                "published": calendar.timegm(published) if published else None,
            })
        return out
    except Exception:
        return []


def _fetch_parallel(jobs: list) -> list[dict]:
    """jobs: list of zero-arg callables each returning list[dict]. Order-stable."""
    results = [None] * len(jobs)
    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
        futures = {pool.submit(job): i for i, job in enumerate(jobs)}
        for fut in as_completed(futures):
            try:
                results[futures[fut]] = fut.result()
            except Exception:
                results[futures[fut]] = []
    return [h for batch in results for h in (batch or [])]


def fetch_rss_rich(ticker: str = TICKER, limit: int = 30) -> list[dict]:
    symbol = TICKER_SYMBOL.get(ticker, ticker[:3]).lower()
    keyword = CURRENCY_MAP.get(ticker, symbol)
    jobs = [(lambda u=url: _parse_feed(u, _feed_source(u))) for url in RSS_FEEDS]
    headlines = [h for h in _fetch_parallel(jobs)
                 if keyword in h["title"].lower() or symbol in h["title"].lower()]
    return headlines[:limit]


def fetch_rss(ticker: str = TICKER, limit: int = 30) -> list[str]:
    return [h["title"] for h in fetch_rss_rich(ticker, limit)]


def fetch_reddit_rich(ticker: str = TICKER, limit: int = 20) -> list[dict]:
    symbol = TICKER_SYMBOL.get(ticker, ticker[:3])
    url = "https://www.reddit.com/r/CryptoCurrency/search.json"
    params = {"q": symbol, "sort": "new", "limit": limit, "t": "day"}
    headers = {"User-Agent": "crypto-trader-bot/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        posts = resp.json()["data"]["children"]
        return [{"title": p["data"]["title"], "source": "reddit",
                 "published": p["data"].get("created_utc")} for p in posts]
    except Exception:
        return []


def fetch_reddit(ticker: str = TICKER, limit: int = 20) -> list[str]:
    return [h["title"] for h in fetch_reddit_rich(ticker, limit)]


def fetch_stock_news_rich(ticker: str, limit: int = 30) -> list[dict]:
    """Stock headlines from Yahoo Finance RSS + Google News RSS — keyless."""
    from src.assets import get_asset
    asset = get_asset(ticker)
    feeds = [
        (f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={asset['yahoo']}&region=US&lang=en-US",
         "yahoo_finance"),
        (f"https://news.google.com/rss/search?q={asset['name'].split(' ')[0]}+stock&hl=en-US&gl=US&ceid=US:en",
         "google_news"),
    ]
    jobs = [(lambda u=url, s=source: _parse_feed(u, s)) for url, source in feeds]
    return _fetch_parallel(jobs)[:limit]


def get_headlines_rich(ticker: str = TICKER) -> list[dict]:
    """Headlines with source + publish time, for weighted sentiment analysis.
    Routes by asset kind: crypto → crypto RSS + Reddit; stocks → Yahoo/Google.
    All sources fetched concurrently."""
    from src.assets import is_crypto
    if is_crypto(ticker):
        combined = _fetch_parallel([
            lambda: fetch_rss_rich(ticker),
            lambda: fetch_reddit_rich(ticker),
        ])
    else:
        combined = fetch_stock_news_rich(ticker)
    seen, unique = set(), []
    for h in combined:
        if h["title"] not in seen:
            seen.add(h["title"])
            unique.append(h)
    return unique[:30]


def get_headlines(ticker: str = TICKER) -> list[str]:
    return [h["title"] for h in get_headlines_rich(ticker)]
