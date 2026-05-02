#!/usr/bin/env python3
"""Smoke-test API keys for OpenAI (required) and Together.ai (optional)."""
import os
import sys


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def check_openai() -> bool:
    _load_dotenv()

    azure_key      = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    openai_key     = os.environ.get("OPENAI_API_KEY")
    is_azure       = bool(azure_key and azure_endpoint)

    if not azure_key and not openai_key:
        print("ERROR: neither OPENAI_API_KEY nor AZURE_OPENAI_API_KEY is set", file=sys.stderr)
        return False

    try:
        if is_azure:
            from openai import AzureOpenAI  # type: ignore[import-not-found]
            api_version = os.environ.get("AZURE_OPENAI_API_VERSION", os.environ.get("AZURE_API_VERSION", "2024-08-01-preview"))
            deployment  = os.environ.get("AZURE_SUBAGENT_DEPLOYMENT", os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"))
            client = AzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=azure_key,
                api_version=api_version,
            )
            client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            print(f"Azure OpenAI: OK (deployment={deployment})")
        else:
            from openai import OpenAI  # type: ignore[import-not-found]
            client = OpenAI(api_key=openai_key)
            client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            print("OpenAI: OK")
        return True
    except Exception as exc:  # noqa: BLE001
        provider = "Azure OpenAI" if is_azure else "OpenAI"
        print(f"ERROR: {provider} call failed: {exc}", file=sys.stderr)
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
