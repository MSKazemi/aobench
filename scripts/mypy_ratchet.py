#!/usr/bin/env python3
"""Fail when `mypy --strict` type debt grows, without demanding a clean tree.

``mypy --strict`` over ``src/aobench/`` still reports pre-existing debt in a
handful of packages, so it cannot be a hard gate yet — CI runs it
``continue-on-error`` for exactly that reason. But "advisory" in practice means
"ignored", and a package that has been cleaned can silently rot back.

This script is the middle ground. It records a per-package error budget in
``mypy_baseline.json`` and fails when:

* a package exceeds its recorded budget, or
* a package with **no** recorded budget reports any error at all — which is the
  case for every already-clean package, and for every package added in future.

The budget can only shrink. When it does, the script says so and exits 1 with
the exact command to record the improvement, so the ratchet tightens instead of
drifting. That is deliberate: a silent improvement is a budget nobody ever
lowers.

Usage::

    python scripts/mypy_ratchet.py            # verify, exit 1 on growth
    python scripts/mypy_ratchet.py --write    # record the current counts
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / "mypy_baseline.json"
TARGET = "src/aobench/"

# `src/aobench/benchmark` is a symlink to the bundled corpus, not source.
_ERROR_RE = re.compile(r"^src/aobench/(?P<package>[^/]+)/.*?:\d+: error:")


def run_mypy() -> str:
    """Run mypy over the source tree and return its stdout.

    A non-zero exit is expected whenever debt remains, so the return code is
    deliberately not checked here — the error lines are the signal.
    """
    proc = subprocess.run(
        ["uv", "run", "mypy", TARGET],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"mypy produced no output (exit {proc.returncode})")
    return proc.stdout


def count_by_package(mypy_output: str) -> Counter[str]:
    """Count error lines per top-level package under ``src/aobench/``."""
    counts: Counter[str] = Counter()
    for line in mypy_output.splitlines():
        if match := _ERROR_RE.match(line):
            counts[match.group("package")] += 1
    return counts


def load_baseline() -> dict[str, int]:
    if not BASELINE_PATH.exists():
        return {}
    data = json.loads(BASELINE_PATH.read_text())
    budgets = data.get("budgets", {})
    return {str(k): int(v) for k, v in budgets.items()}


def write_baseline(counts: Counter[str]) -> None:
    payload = {
        "_comment": (
            "Per-package `mypy --strict` error budgets. A package absent from this "
            "map must report zero errors. Budgets may only shrink — regenerate with "
            "`python scripts/mypy_ratchet.py --write` after paying debt down."
        ),
        "total": sum(counts.values()),
        "budgets": dict(sorted(counts.items())),
    }
    BASELINE_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="record the current per-package counts as the new budget",
    )
    args = parser.parse_args()

    counts = count_by_package(run_mypy())
    total = sum(counts.values())

    if args.write:
        write_baseline(counts)
        print(f"mypy baseline written — {total} errors across {len(counts)} packages")
        return 0

    baseline = load_baseline()
    if not baseline and not BASELINE_PATH.exists():
        print(f"no baseline at {BASELINE_PATH.name}; run with --write to create one")
        return 1

    regressions: list[str] = []
    improvements: list[str] = []

    for package in sorted(set(counts) | set(baseline)):
        actual = counts.get(package, 0)
        budget = baseline.get(package, 0)
        if actual > budget:
            where = f"budget {budget}" if package in baseline else "expected clean"
            regressions.append(f"  {package}: {actual} errors ({where})")
        elif actual < budget:
            improvements.append(f"  {package}: {actual} errors (budget {budget})")

    if regressions:
        print("mypy type debt grew:\n" + "\n".join(regressions), file=sys.stderr)
        print(
            "\nFix the new errors, or — if this package is genuinely allowed more "
            "debt —\nrecord it deliberately with: python scripts/mypy_ratchet.py --write",
            file=sys.stderr,
        )
        return 1

    if improvements:
        print("mypy type debt shrank — tighten the ratchet:\n" + "\n".join(improvements))
        print("\nRecord it with: python scripts/mypy_ratchet.py --write")
        return 1

    clean = sum(1 for p in counts if counts[p] == 0)
    print(
        f"mypy ratchet OK — {total} errors, all within budget "
        f"({len(baseline)} packages carrying debt, {clean} at zero)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
