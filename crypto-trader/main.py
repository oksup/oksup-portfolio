#!/usr/bin/env python3
"""
Standalone pipeline: fetch headlines → keyword sentiment → execute (paper trade).
Used by manual runs and the dashboard "Run now" button — no API key required.

Note: the scheduled Claude Routine uses a smarter LLM analysis instead
(see fetch_headlines.py + execute_signal.py). This script is the offline path.
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import logging
from src.config import TICKER, LOG_PATH
from src.sentiment.scraper import get_headlines_rich
from src.sentiment.analyzer import analyze
from src.trader.db import init_db
from src.trader.executor import execute

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)


def run(ticker: str = TICKER, dry_run: bool = False):
    log.info(f"=== Pipeline start | ticker={ticker} dry_run={dry_run} ===")
    init_db()

    log.info("Fetching headlines...")
    headlines = get_headlines_rich(ticker)
    log.info(f"Got {len(headlines)} headlines")

    log.info("Analyzing sentiment (weighted keyword heuristic)...")
    analysis = analyze(headlines, ticker)
    log.info(
        f"Signal: {analysis['signal']} | confidence: {analysis['confidence']:.2f} | "
        f"reason: {analysis['reasoning']}"
    )

    log.info("Executing...")
    result = execute(analysis, ticker, dry_run=dry_run)
    log.info(f"Result: {result}")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default=TICKER)
    parser.add_argument("--dry-run", action="store_true", help="Log signal but skip order placement")
    args = parser.parse_args()
    run(args.ticker, dry_run=args.dry_run)
