"""check_validity_gates.py — Run validity gates V1–V6 before committing paper results.

Input:
  - data/runs/v01_dev_*/    (3 model run directories)
  - data/robustness/v01_*.json  (15 robustness files)

Output: Pass/fail report for V1–V6 gates (stdout or --output file)

Usage:
    python3 scripts/check_validity_gates.py
    python3 scripts/check_validity_gates.py --output data/reports/validity_gates.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULT_RUN_DIRS = [
    "data/runs/v01_dev_claude_sonnet",
    "data/runs/v01_dev_gpt4o",
    "data/runs/v01_dev_gpt4o_mini",
]
DEFAULT_ROB_DIR = "data/robustness"

ROBUSTNESS_TASKS = [
    "JOB_USR_001",
    "JOB_SYS_002",
    "MON_SYS_003",
    "ENERGY_FAC_003",
    "MON_SYS_006",
]
MODEL_SLUG_MAP = {
    "claude": "Claude-Sonnet-4.6",
    "gpt4o_mini": "GPT-4o-mini",
    "gpt4o": "GPT-4o",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def find_summary(run_dir: str) -> Path | None:
    base = Path(run_dir)
    if not base.exists():
        return None
    direct = base / "run_summary.json"
    if direct.exists():
        return direct
    for child in sorted(base.iterdir()):
        candidate = child / "run_summary.json"
        if candidate.exists():
            return candidate
    return None


def find_results(run_dir: str) -> list[dict]:
    """Return list of result dicts from run_dir/*/results/*_result.json."""
    base = Path(run_dir)
    results = []
    # Try run_dir/results/ or run_dir/<run_id>/results/
    for pattern in ["results/*_result.json", "*/results/*_result.json"]:
        for f in base.glob(pattern):
            try:
                results.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
    return results


def load_model_data(run_dirs: list[str]) -> list[dict]:
    """Return list of {label, summary, results} per model."""
    models = []
    for run_dir in run_dirs:
        sp = find_summary(run_dir)
        if sp is None:
            print(f"  WARNING: No run_summary.json in {run_dir}", file=sys.stderr)
            continue
        summary = json.loads(sp.read_text(encoding="utf-8"))
        results = find_results(run_dir)
        label = summary.get("model_name") or summary.get("adapter_name") or Path(run_dir).name
        models.append({"label": label, "summary": summary, "results": results, "run_dir": run_dir})
    return models


def load_robustness(rob_dir: str) -> dict[str, dict[str, dict]]:
    """Return {task_id: {model_slug: stats}}."""
    base = Path(rob_dir)
    result: dict[str, dict[str, dict]] = {t: {} for t in ROBUSTNESS_TASKS}
    for f in sorted(base.glob("v01_*.json")):
        raw = f.stem[len("v01_"):]
        for slug in sorted(MODEL_SLUG_MAP.keys(), key=len, reverse=True):
            if raw.startswith(slug + "_"):
                task_id = raw[len(slug) + 1:]
                if task_id in ROBUSTNESS_TASKS:
                    try:
                        result[task_id][slug] = json.loads(f.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                break
    return result


# ── Gates ──────────────────────────────────────────────────────────────────────

def gate_v1(models: list[dict]) -> dict:
    """V1: All tasks execute without crash (no framework_error, no missing results)."""
    issues = []
    for m in models:
        results = m["results"]
        if not results:
            issues.append(f"{m['label']}: no results found")
            continue
        for r in results:
            ec = r.get("error_category")
            if ec == "framework_error":
                issues.append(f"{m['label']}/{r.get('task_id')}: error_category=framework_error")

    return {
        "gate": "V1",
        "name": "All tasks execute without crash",
        "passed": len(issues) == 0,
        "issues": issues,
    }


def gate_v2(models: list[dict]) -> dict:
    """V2: RBAC hard-fail rate < 30% for all models."""
    issues = []
    details = []
    for m in models:
        results = m["results"]
        if not results:
            continue
        hard_fail_count = sum(1 for r in results if r.get("hard_fail"))
        ratio = hard_fail_count / len(results)
        details.append(f"{m['label']}: {hard_fail_count}/{len(results)} = {ratio:.2%}")
        if ratio >= 0.30:
            issues.append(f"{m['label']}: hard_fail_rate={ratio:.2%} >= 30%")

    return {
        "gate": "V2",
        "name": "RBAC hard-fail sanity check (< 30% threshold)",
        "passed": len(issues) == 0,
        "details": details,
        "issues": issues,
    }


def gate_v3(models: list[dict]) -> dict:
    """V3: Score distribution non-degenerate (mean ∈ [0.15, 0.95])."""
    issues = []
    details = []
    for m in models:
        mean = m["summary"].get("mean_aggregate_score")
        if mean is None:
            issues.append(f"{m['label']}: mean_aggregate_score missing from summary")
            continue
        details.append(f"{m['label']}: mean={mean:.4f}")
        if mean < 0.15:
            issues.append(f"{m['label']}: mean={mean:.4f} < 0.15 (floor effect)")
        elif mean > 0.95:
            issues.append(f"{m['label']}: mean={mean:.4f} > 0.95 (ceiling effect)")

    return {
        "gate": "V3",
        "name": "Score distribution non-degenerate [0.15, 0.95]",
        "passed": len(issues) == 0,
        "details": details,
        "issues": issues,
    }


def gate_v4(rob_data: dict[str, dict[str, dict]]) -> dict:
    """V4: pass^8 ∈ [0.10, 0.90] for at least 3 of 5 representative tasks (any model)."""
    issues = []
    details = []
    pass_k_values = []

    for task_id in ROBUSTNESS_TASKS:
        for slug, stats in rob_data[task_id].items():
            pk = stats.get("pass_k", {})
            v = pk.get(8) or pk.get("8")
            if v is not None:
                pass_k_values.append((task_id, slug, float(v)))
                details.append(f"{task_id}/{MODEL_SLUG_MAP.get(slug, slug)}: pass^8={float(v):.4f}")

    # Count tasks where pass^8 ∈ [0.10, 0.90] across any model
    tasks_in_range: set[str] = set()
    for task_id, slug, v in pass_k_values:
        if 0.10 <= v <= 0.90:
            tasks_in_range.add(task_id)

    count_in_range = len(tasks_in_range)

    if pass_k_values:
        all_values = [v for _, _, v in pass_k_values]
        value_range = max(all_values) - min(all_values)
        details.append(f"pass^8 range across tasks: {value_range:.4f} (target >= 0.30)")
        if value_range < 0.30:
            issues.append(f"pass^8 range={value_range:.4f} < 0.30 across 5 tasks")

        if all(v == 1.0 for _, _, v in pass_k_values):
            issues.append("All pass^8 = 1.0 (tasks are deterministic/trivial)")
        elif all(v == 0.0 for _, _, v in pass_k_values):
            issues.append("All pass^8 = 0.0 (tasks are too stochastic)")
        elif count_in_range < 3:
            issues.append(f"Only {count_in_range}/5 tasks have pass^8 ∈ [0.10, 0.90] (need >= 3)")
    else:
        issues.append("No robustness data loaded — run robustness suite first")

    return {
        "gate": "V4",
        "name": "Robustness non-trivial (pass^8 ∈ [0.10, 0.90] for >= 3/5 tasks)",
        "passed": len(issues) == 0,
        "tasks_in_range": count_in_range,
        "details": details,
        "issues": issues,
    }


def gate_v5(models: list[dict]) -> dict:
    """V5: Inter-model score spread >= 0.08."""
    means = []
    details = []
    for m in models:
        mean = m["summary"].get("mean_aggregate_score")
        if mean is not None:
            means.append(mean)
            details.append(f"{m['label']}: mean={mean:.4f}")

    issues = []
    spread = None
    if len(means) >= 2:
        spread = round(max(means) - min(means), 4)
        details.append(f"Spread: {spread:.4f} (threshold: 0.08)")
        if spread < 0.08:
            issues.append(f"Spread={spread:.4f} < 0.08 (benchmark does not discriminate)")
    else:
        issues.append(f"Need >= 2 models with scores, only have {len(means)}")

    return {
        "gate": "V5",
        "name": "Inter-model score spread >= 0.08",
        "passed": len(issues) == 0,
        "spread": spread,
        "details": details,
        "issues": issues,
    }


def gate_v6(models: list[dict]) -> dict:
    """V6: GPT-4o / GPT-4o-mini cost ratio >= 3.0."""
    cost_by_model: dict[str, float] = {}
    issues = []
    details = []

    for m in models:
        label = m["label"]
        results = m["results"]
        costs = [r.get("cost_estimate_usd") for r in results if r.get("cost_estimate_usd") is not None]
        if costs:
            total = sum(costs)
            cost_by_model[label] = total
            details.append(f"{label}: total_cost=${total:.4f} ({len(costs)} tasks)")
        else:
            details.append(f"{label}: cost_estimate_usd not populated (adapter may not report costs)")

    # Find GPT-4o and GPT-4o-mini costs
    gpt4o_cost = None
    mini_cost = None
    for label, cost in cost_by_model.items():
        lc = label.lower()
        if "gpt-4o-mini" in lc or "gpt4o-mini" in lc or "gpt4o_mini" in lc:
            mini_cost = cost
        elif "gpt-4o" in lc or "gpt4o" in lc:
            gpt4o_cost = cost

    ratio = None
    if gpt4o_cost is not None and mini_cost is not None and mini_cost > 0:
        ratio = round(gpt4o_cost / mini_cost, 2)
        details.append(f"Cost ratio GPT-4o / GPT-4o-mini = {ratio:.2f} (threshold: 3.0)")
        if ratio < 3.0:
            issues.append(f"Cost ratio={ratio:.2f} < 3.0 (check adapter cost reporting)")
    elif gpt4o_cost is None or mini_cost is None:
        issues.append("Could not find both GPT-4o and GPT-4o-mini cost data")

    return {
        "gate": "V6",
        "name": "Cost spread: GPT-4o / GPT-4o-mini >= 3.0",
        "passed": len(issues) == 0,
        "ratio": ratio,
        "details": details,
        "issues": issues,
    }


# ── Report ─────────────────────────────────────────────────────────────────────

def print_report(gates: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("ExaBench v0.1 — Validity Gate Report")
    print("=" * 60)
    for g in gates:
        status = "✅ PASS" if g["passed"] else "❌ FAIL"
        print(f"\n{g['gate']}: {g['name']}")
        print(f"  Status: {status}")
        for d in g.get("details", []):
            print(f"  ·  {d}")
        for iss in g.get("issues", []):
            print(f"  ⚠  {iss}")

    all_pass = all(g["passed"] for g in gates)
    print("\n" + "─" * 60)
    if all_pass:
        print("✅ ALL GATES PASS — results may enter the paper.")
    else:
        failed = [g["gate"] for g in gates if not g["passed"]]
        print(f"❌ GATES FAILED: {', '.join(failed)}")
        print("   Investigate failures before publishing results.")
    print("=" * 60 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dirs",
        nargs="*",
        default=DEFAULT_RUN_DIRS,
        help="Run directories (default: v01_dev_*)",
    )
    parser.add_argument("--rob-dir", default=DEFAULT_ROB_DIR)
    parser.add_argument("--output", "-o", default=None, help="Write JSON report here")
    args = parser.parse_args(argv)

    print("Loading model run data...")
    models = load_model_data(args.run_dirs)
    print(f"  Loaded {len(models)} model(s).")

    print("Loading robustness data...")
    rob_data = load_robustness(args.rob_dir)
    n_rob = sum(len(v) for v in rob_data.values())
    print(f"  Loaded {n_rob} robustness entries.")

    gates = [
        gate_v1(models),
        gate_v2(models),
        gate_v3(models),
        gate_v4(rob_data),
        gate_v5(models),
        gate_v6(models),
    ]

    print_report(gates)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(gates, indent=2), encoding="utf-8")
        print(f"JSON report written: {args.output}")

    all_pass = all(g["passed"] for g in gates)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
