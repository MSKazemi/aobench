#!/usr/bin/env python3
"""Print v0.2 experiment budget spend vs. remaining.

Hard-coded v0.2 budget breakdown (informational):
  E1 = $65, E2 = $5, E6 = $11, total = $81, limit = $100
The limit is configurable via AOBENCH_BUDGET_USD (default: 100).
"""
import json
import os
import pathlib
import sys

# v0.2 budget components (informational only)
_BUDGET_COMPONENTS = {"E1": 65.0, "E2": 5.0, "E6": 11.0}

RUNS_DIR = pathlib.Path("data/runs")


def scan_compute_files(runs_dir: pathlib.Path) -> tuple[float, int]:
    """Return (total_usd_spent, num_runs) by summing all COMPUTE.json files."""
    total = 0.0
    count = 0
    if not runs_dir.exists():
        return total, count

    for compute_file in runs_dir.glob("*/COMPUTE.json"):
        try:
            with open(compute_file) as f:
                data = json.load(f)
            value = data.get("total_usd", 0.0)
            total += float(value)
            count += 1
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            print(f"WARNING: could not read {compute_file}: {exc}", file=sys.stderr)

    return total, count


def main() -> int:
    limit = float(os.environ.get("AOBENCH_BUDGET_USD", "100"))
    spent, num_runs = scan_compute_files(RUNS_DIR)
    remaining = limit - spent

    print(f"Budget limit:   ${limit:>7.2f}")
    print(f"Spent so far:   ${spent:>7.2f}  ({num_runs} run(s))")
    print(f"Remaining:      ${remaining:>7.2f}")

    if spent > limit:
        print(
            f"ERROR: budget exceeded (${spent:.2f} > ${limit:.2f})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
