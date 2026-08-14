"""
Eval harness. Run this before and after every change.

This is the difference between "I think the bot still works" and knowing.
It is also how you prove a Pro -> Flash downgrade is safe: run it on both,
compare the pass rate, and only downgrade the channels that hold.

Usage:
    python evals/run_evals.py
    FORCE_ROLE=fast  python evals/run_evals.py    # test the cheap model
    FORCE_ROLE=smart python evals/run_evals.py    # test the strong model
"""

# Lets this file use modern type-hint syntax on older Pythons (3.7+).
from __future__ import annotations

import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from agent import run_agent  # noqa: E402
from config import FORCE_ROLE, MODELS, PROVIDER  # noqa: E402

logging.basicConfig(level=logging.WARNING)

CASES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases.jsonl")


def load_cases() -> list[dict]:
    with open(CASES_PATH, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main() -> int:
    cases = load_cases()
    print(f"provider={PROVIDER} models={MODELS} force_role={FORCE_ROLE or '(per-channel)'}")
    print(f"running {len(cases)} cases\n")

    passed, failed = 0, []

    for i, case in enumerate(cases, 1):
        channel = case["channel"]
        message = case["message"]
        expected = case.get("expect_tool")

        try:
            _reply, calls = run_agent(channel, message, history=[])
        except Exception as exc:  # noqa: BLE001
            failed.append((i, message, expected, f"EXCEPTION: {exc}"))
            print(f"{i:3d}. ERROR  #{channel:6s} {message[:52]:52s}  {exc}")
            continue

        actual = calls[0][0] if calls else None
        ok = actual == expected

        if ok:
            passed += 1
        else:
            failed.append((i, message, expected, actual))

        status = "pass" if ok else "FAIL"
        print(
            f"{i:3d}. {status}   #{channel:6s} {message[:52]:52s}  "
            f"expected={expected or 'no tool':14s} got={actual or 'no tool'}"
        )

    print(f"\n{passed}/{len(cases)} passed")

    if failed:
        print("\nFailures:")
        for i, message, expected, actual in failed:
            print(f"  {i:3d}. {message}\n       expected {expected}, got {actual}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
