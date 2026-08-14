"""
Keyword-based sentiment analyzer — no API key required.

This is the standalone fallback used by main.py and the dashboard "Run now"
button. The scheduled Claude Routine does a smarter LLM-based analysis; this
heuristic gives an instant, free, offline signal for manual runs.
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9
from src.config import TICKER

BULLISH_TERMS = [
    "surge", "rally", "soar", "inflow", "adoption", "accumulat", "buy", "bought",
    "record high", "all-time high", "ath", "institutional", "etf approv", "bullish",
    "breakout", "upgrade", "treasury", "rate cut", "gains", "pump", "jump", "rebound",
    "backs", "strengthens", "buyback", "enters bitcoin", "rushing into",
    # stock-flavored
    "beats expectations", "beats estimates", "earnings beat", "record revenue",
    "raises guidance", "raises forecast", "dividend increase", "price target raised",
    "outperform", "strong demand", "expands",
]

BEARISH_TERMS = [
    "crash", "plunge", "drop", "dump", "selloff", "sell-off", "outflow", "fraud",
    "hack", "lawsuit", "charges", "ban", "crackdown", "investigation", "bearish",
    "decline", "fear", "liquidat", "shut down", "money laundering", "sheds", "cuts debt",
    "selloff deepens", "falling", "pressure", "bottom", "predatory", "threat", "volatility",
    # stock-flavored
    "misses expectations", "misses estimates", "earnings miss", "lowers guidance",
    "cuts forecast", "downgrade", "layoffs", "recall", "antitrust", "sec probe",
    "underperform", "weak demand", "slowdown",
]


# how much a headline counts, by where it came from
SOURCE_WEIGHTS = {
    "coindesk": 1.0, "cointelegraph": 0.9, "decrypt": 0.8,
    "bitcoinmagazine": 0.8, "yahoo_finance": 0.9, "google_news": 0.8,
    "rss": 0.7, "reddit": 0.5,
}
RECENCY_HALF_LIFE_H = 12.0   # a 12-hour-old headline counts half as much


def _score(headline: str) -> str:
    h = headline.lower()
    bull = sum(1 for t in BULLISH_TERMS if t in h)
    bear = sum(1 for t in BEARISH_TERMS if t in h)
    if bull > bear:
        return "BULLISH"
    if bear > bull:
        return "BEARISH"
    return "NEUTRAL"


def _weight(item: dict, ticker: str) -> float:
    """source reliability × recency decay × asset relevance, in (0, 1]."""
    import time
    w = SOURCE_WEIGHTS.get(item.get("source", ""), 0.7)
    published = item.get("published")
    if published:
        age_h = max(0.0, (time.time() - published) / 3600)
        w *= 0.5 ** (age_h / RECENCY_HALF_LIFE_H)
    else:
        w *= 0.8  # unknown age — mild discount
    from src.assets import get_asset
    terms = get_asset(ticker)["terms"]
    if not any(t in item["title"].lower() for t in terms):
        w *= 0.5  # news not naming this asset counts half
    return w


def analyze(headlines: list, ticker: str = TICKER) -> dict:
    """headlines: list of titles (str) or rich dicts {title, source, published}."""
    if not headlines:
        return {
            "signal": "HOLD",
            "confidence": 0.0,
            "reasoning": "No headlines available",
            "classified_headlines": [],
        }

    items = [h if isinstance(h, dict) else {"title": h} for h in headlines]
    classified = [{
        "headline": it["title"],
        "sentiment": _score(it["title"]),
        "weight": round(_weight(it, ticker), 3),
    } for it in items]
    bull = sum(c["weight"] for c in classified if c["sentiment"] == "BULLISH")
    bear = sum(c["weight"] for c in classified if c["sentiment"] == "BEARISH")
    directional = bull + bear

    if directional == 0:
        signal, confidence = "HOLD", 0.3
        reasoning = f"All {len(headlines)} headlines neutral — no directional edge"
    else:
        bull_ratio = bull / directional
        if bull_ratio >= 0.6:
            signal = "BUY"
            confidence = round(0.55 + (bull_ratio - 0.6) * 0.875, 2)
            reasoning = (f"Weighted sentiment {bull:.1f} bullish vs {bear:.1f} bearish "
                         f"(source/recency/relevance-weighted) indicates upward momentum")
        elif bull_ratio <= 0.4:
            signal = "SELL"
            confidence = round(0.55 + (0.4 - bull_ratio) * 0.875, 2)
            reasoning = (f"Weighted sentiment {bear:.1f} bearish vs {bull:.1f} bullish "
                         f"(source/recency/relevance-weighted) indicates downward pressure")
        else:
            signal = "HOLD"
            confidence = round(0.4 + abs(bull_ratio - 0.5) * 0.4, 2)
            reasoning = (f"Mixed weighted sentiment ({bull:.1f} bullish, {bear:.1f} bearish) "
                         f"— insufficient edge")

    return {
        "signal": signal,
        "confidence": min(confidence, 0.95),
        "reasoning": reasoning,
        "classified_headlines": classified,
    }
