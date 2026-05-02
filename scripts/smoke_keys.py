#!/usr/bin/env python3
"""Smoke-test API keys for OpenAI (required) and Together.ai (optional)."""
import os
import sys


def check_openai() -> bool:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
    if not api_key:
        print("ERROR: neither OPENAI_API_KEY nor AZURE_OPENAI_API_KEY is set", file=sys.stderr)
        return False

    # Try a minimal API call to verify the key works.
    try:
        import openai  # type: ignore[import-not-found]

        client = openai.OpenAI(api_key=api_key)
        client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        print("OpenAI: OK")
        return True
    except ImportError:
        pass  # fall back to urllib

    # urllib fallback
    import json
    import urllib.error
    import urllib.request

    payload = json.dumps(
        {
            "model": "gpt-4o-mini-2024-07-18",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        print("OpenAI: OK")
        return True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"ERROR: OpenAI API returned HTTP {exc.code}: {body}", file=sys.stderr)
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: OpenAI API call failed: {exc}", file=sys.stderr)
        return False


def check_together() -> None:
    if os.environ.get("TOGETHER_API_KEY"):
        print("Together.ai: key present (not tested)")
    else:
        print("Together.ai: TOGETHER_API_KEY not set (skipping)")


def main() -> int:
    openai_ok = check_openai()
    check_together()
    return 0 if openai_ok else 1


if __name__ == "__main__":
    sys.exit(main())
