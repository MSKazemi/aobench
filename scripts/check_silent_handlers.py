#!/usr/bin/env python3
"""Fail when a new broad `except` swallows a failure instead of surfacing it.

Six defects in this codebase have shared one shape: a real error caught by a
broad handler and converted into a plausible-looking success, so nothing ever
raised and no test went red. Among them —

* `AOBenchEnv.step()` reported every tool call as forbidden, because the guard
  read an attribute `ToolRegistry` does not have.
* The Langfuse exporter dropped `session_id`/`user_id`/tags from every trace,
  because it read a private attribute the SDK had renamed and the resulting
  `AttributeError` went into `except Exception: logger.debug(...)`.
* F1–F3 passed a bundle whose `slurm_state.json` was corrupt, reporting it as
  "skipped (no slurm_state.json)".
* The leaderboard silently dropped unreadable result files, shrinking `n_runs`
  and every `pass@k` derived from it.

A broad handler is not wrong by itself — several in this tree are correct, and
they are recorded in the baseline with the reason. What this checks is that no
*new* one appears unreviewed.

Like `scripts/mypy_ratchet.py`, this is a ratchet rather than a clean-tree gate:
`silent_handlers_baseline.json` records the accepted sites, and the check fails
when a site appears that is not in it.

Usage::

    python scripts/check_silent_handlers.py            # verify, exit 1 on a new site
    python scripts/check_silent_handlers.py --write    # accept the current set
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "aobench"
BASELINE_PATH = ROOT / "silent_handlers_baseline.json"

# Log calls below WARNING do not surface a failure to anyone running the tool.
_QUIET_LOG_METHODS = {"debug", "info"}


def _is_broad(handler: ast.ExceptHandler) -> bool:
    """True for `except:` / `except Exception:` / `except BaseException:`."""
    if handler.type is None:
        return True
    return isinstance(handler.type, ast.Name) and handler.type.id in {
        "Exception",
        "BaseException",
    }


def _significant_body(handler: ast.ExceptHandler) -> list[ast.stmt]:
    """The handler body, ignoring a bare docstring-style string expression."""
    return [
        node
        for node in handler.body
        if not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
    ]


def _classify(handler: ast.ExceptHandler) -> str | None:
    """Return why this handler is silent, or None if it surfaces the failure."""
    body = _significant_body(handler)
    if not body:
        return None

    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return "pass"

    # Only quiet logging: nothing reaches a user at default verbosity.
    if all(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) for n in body):
        methods = set()
        for node in body:
            func = node.value.func  # type: ignore[attr-defined]
            if not isinstance(func, ast.Attribute):
                return None
            methods.add(func.attr)
        if methods and methods <= _QUIET_LOG_METHODS:
            return f"only logger.{sorted(methods)[0]}()"
        return None

    # A lone `return <plausible value>`: the caller cannot tell a computed
    # result from a swallowed failure.
    if len(body) == 1 and isinstance(body[0], ast.Return):
        value = body[0].value
        if value is None:
            return "return None"
        if isinstance(value, ast.Constant):
            return f"return {value.value!r}"
        if isinstance(value, (ast.List, ast.Dict, ast.Tuple, ast.Set)):
            if not getattr(value, "elts", None) and not getattr(value, "keys", None):
                return f"return empty {type(value).__name__.lower()}"
    return None


def collect() -> dict[str, str]:
    """Map "<path>:<function>" -> why it is silent, for every offending handler."""
    found: dict[str, str] = {}
    for path in sorted(SRC.rglob("*.py")):
        # src/aobench/benchmark is a symlink to the bundled corpus, not source.
        if "/benchmark/" in path.as_posix():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        # Anchor each site to its enclosing function rather than a line number,
        # so that editing code above a handler does not invalidate the baseline.
        enclosing: dict[ast.AST, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    enclosing.setdefault(child, node.name)

        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                if not _is_broad(handler):
                    continue
                reason = _classify(handler)
                if reason is None:
                    continue
                where = enclosing.get(handler, "<module>")
                key = f"{rel}::{where}"
                # A function with several silent handlers collapses to one entry;
                # the reason of the first is representative enough for review.
                found.setdefault(key, reason)
    return found


def load_baseline() -> dict[str, str]:
    if not BASELINE_PATH.exists():
        return {}
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.get("accepted", {}).items()}


def write_baseline(found: dict[str, str]) -> None:
    payload = {
        "_comment": (
            "Broad `except` handlers that do not surface the failure, reviewed and "
            "accepted. A site not listed here fails `make silent-handlers-check`. "
            "Before adding one, check the handler cannot hide an API change: that is "
            "how the gym, langfuse, fidelity and leaderboard defects survived. "
            "Regenerate with `python scripts/check_silent_handlers.py --write`."
        ),
        "count": len(found),
        "accepted": dict(sorted(found.items())),
    }
    BASELINE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="accept the current set of silent handlers as the baseline",
    )
    args = parser.parse_args()

    found = collect()

    if args.write:
        write_baseline(found)
        print(f"silent-handler baseline written — {len(found)} accepted sites")
        return 0

    if not BASELINE_PATH.exists():
        print(f"no baseline at {BASELINE_PATH.name}; run with --write to create one")
        return 1

    baseline = load_baseline()
    new = {k: v for k, v in found.items() if k not in baseline}
    gone = sorted(k for k in baseline if k not in found)

    if new:
        print("new silent exception handler(s):", file=sys.stderr)
        for key, reason in sorted(new.items()):
            print(f"  {key}  [{reason}]", file=sys.stderr)
        print(
            "\nA broad `except` that passes, logs below WARNING, or returns a "
            "plausible value\nturns a real failure into a valid-looking result. "
            "Either surface it — log at\nWARNING, or return something the caller can "
            "distinguish — or, if it is genuinely\ncorrect, record it deliberately with:"
            "\n    make silent-handlers-accept",
            file=sys.stderr,
        )
        return 1

    if gone:
        print("silent handlers removed — tighten the baseline:")
        for key in gone:
            print(f"  {key}")
        print("\nRecord it with: make silent-handlers-accept")
        return 1

    print(f"silent-handler check OK — {len(found)} accepted sites, no new ones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
