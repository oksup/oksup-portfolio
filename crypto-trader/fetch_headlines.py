#!/usr/bin/env python3
"""
Fetch headlines and print as JSON for the Claude Routine to read and analyze.
Usage: python3 fetch_headlines.py [--ticker BTCUSDT]
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from src.config import TICKER
from src.sentiment.scraper import get_headlines_rich

parser = argparse.ArgumentParser()
parser.add_argument("--ticker", default=TICKER)
args = parser.parse_args()

rich = get_headlines_rich(args.ticker)
# include source + age so the Claude Routine can weight recency/reliability
import time
headlines = [{
    "title": h["title"],
    "source": h.get("source", "rss"),
    "age_hours": round((time.time() - h["published"]) / 3600, 1) if h.get("published") else None,
} for h in rich]
print(json.dumps({"ticker": args.ticker, "count": len(headlines), "headlines": headlines}, indent=2))
