"""
Shows which Gemini models YOUR API key can actually use.

Google retires model IDs for new keys without warning, so the names in a
tutorial can be dead by the time you read it. This asks Google directly.

Run it whenever you get a 404 saying a model is no longer available:

    python list_models.py

Then copy a name from the list into the "gemini" block in config.py.
Uses only the Python standard library, nothing to install.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def main() -> int:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY is not set. Check your .env file.")
        return 1

    try:
        with urllib.request.urlopen(f"{ENDPOINT}?key={key}&pageSize=200", timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f"Google rejected the request ({exc.code}).")
        print("Usually that means the API key is wrong. Make a new one at:")
        print("  https://aistudio.google.com/apikey")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Could not reach Google: {exc}")
        return 1

    models = data.get("models", [])
    usable = [
        m for m in models if "generateContent" in m.get("supportedGenerationMethods", [])
    ]

    if not usable:
        print("No usable models returned. That is unexpected; check your key.")
        return 1

    print(f"\n{len(usable)} models your key can use for chat:\n")
    for m in sorted(usable, key=lambda x: x["name"]):
        # API returns "models/gemini-3.6-flash"; strip the prefix.
        model_id = m["name"].split("/", 1)[-1]
        label = m.get("displayName", "")
        print(f"  gemini/{model_id:<40s} {label}")

    print("\nTo use one, put its full name (including the 'gemini/' part)")
    print("into MODELS_BY_PROVIDER['gemini'] in config.py.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
