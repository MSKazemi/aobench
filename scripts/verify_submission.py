#!/usr/bin/env python3
"""verify_submission.py — Run V0–V6 validity gates on a submitted result.

Usage:
    python3 scripts/verify_submission.py --run-dir data/runs/v01_dev_gpt4o/run_XXXX

Exits 0 if all required gates pass (or if --fail-on-error is not set),
1 if any gate fails (only when --fail-on-error is set), 2 on input error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def check_v0_schema(results: list[dict]) -> tuple[bool, str]:
    """V0: All result rows have required fields."""
    required = {"task_id", "aggregate_score"}
    missing = [r.get("task_id", "<unknown>") for r in results if not required.issubset(r)]
    if missing:
        return False, f"V0 FAIL: {len(missing)} rows missing required fields: {missing[:5]}"
    return True, f"V0 PASS: {len(results)} rows with required fields"


def check_v1_all_tasks_ran(results: list[dict], summary: dict) -> tuple[bool, str]:
    """V1: No framework_error tasks."""
    errors = [r["task_id"] for r in results if r.get("error_category") == "framework_error"]
    if errors:
        return False, f"V1 FAIL: {len(errors)} framework_error tasks: {errors[:5]}"
    return True, "V1 PASS: 0 framework_error tasks"


def check_v2_hard_fail_rate(results: list[dict]) -> tuple[bool, str]:
    """V2: Hard-fail rate < 30%."""
    total = len(results)
    if total == 0:
        return True, "V2 SKIP: no results"
    hard_fails = sum(
        1
        for r in results
        if r.get("hard_fail")
        or (r.get("violation_vector") or {}).get("hard_fail_trigger", False)
    )
    rate = hard_fails / total
    if rate >= 0.30:
        return False, f"V2 FAIL: hard_fail rate {rate:.1%} >= 30% ({hard_fails}/{total})"
    return True, f"V2 PASS: hard_fail rate {rate:.1%} ({hard_fails}/{total})"


def check_v3_score_range(results: list[dict]) -> tuple[bool, str]:
    """V3: Mean aggregate score in [0.15, 0.95]."""
    scores = [r.get("aggregate_score") for r in results if r.get("aggregate_score") is not None]
    if not scores:
        return True, "V3 SKIP: no aggregate_score values"
    mean = sum(scores) / len(scores)
    if not (0.15 <= mean <= 0.95):
        return False, f"V3 FAIL: mean_aggregate={mean:.3f} not in [0.15, 0.95]"
    return True, f"V3 PASS: mean_aggregate={mean:.3f}"


def check_v5_inter_model_spread(results: list[dict]) -> tuple[bool, str]:
    """V5: Score spread >= 0.08 (non-trivial task discrimination)."""
    scores = [r.get("aggregate_score") for r in results if r.get("aggregate_score") is not None]
    if len(scores) < 2:
        return True, "V5 SKIP: fewer than 2 tasks"
    spread = max(scores) - min(scores)
    if spread < 0.08:
        return False, f"V5 FAIL: score spread {spread:.3f} < 0.08 (all scores similar)"
    return True, f"V5 PASS: score spread {spread:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify an AOBench run against V0-V6 validity gates."
    )
    ap.add_argument("--run-dir", required=True, help="Path to a run directory (contains results/)")
    ap.add_argument("--gates", default="V0,V1,V2,V3,V5", help="Comma-separated gates to check")
    ap.add_argument(
        "--fail-on-error", action="store_true", help="Exit 1 if any gate fails"
    )
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    results_dir = run_dir / "results"

    if not results_dir.is_dir():
        print(f"Error: {results_dir} not found", file=sys.stderr)
        return 2

    results: list[dict] = []
    for f in sorted(results_dir.glob("*.json")):
        try:
            results.append(json.loads(f.read_text()))
        except Exception as e:
            print(f"Warning: could not read {f}: {e}", file=sys.stderr)

    summary_path = run_dir / "run_summary.json"
    summary: dict = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text())
        except Exception:
            pass

    requested = set(args.gates.split(","))
    gate_fns = {
        "V0": lambda: check_v0_schema(results),
        "V1": lambda: check_v1_all_tasks_ran(results, summary),
        "V2": lambda: check_v2_hard_fail_rate(results),
        "V3": lambda: check_v3_score_range(results),
        "V5": lambda: check_v5_inter_model_spread(results),
    }

    failures = []
    for gate in sorted(requested):
        if gate not in gate_fns:
            print(f"Unknown gate: {gate}")
            continue
        ok, msg = gate_fns[gate]()
        print(msg)
        if not ok:
            failures.append(gate)

    if failures:
        print(f"\nFAILED gates: {failures}", file=sys.stderr)
        return 1 if args.fail_on_error else 0
    print(f"\nAll {len(requested)} gate(s) PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
