#!/usr/bin/env python3
"""E4 ablation: sensitivity of CuP pass rate to score threshold.

CuP = 1 if aggregate_score >= threshold AND NOT hard_fail, else 0.
Three variants: strict (0.70), tolerant_1 (0.60), tolerant_2 (0.50).

Outputs data/ablations/cup_threshold.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Threshold variants
# ---------------------------------------------------------------------------

THRESHOLD_VARIANTS: dict[str, float] = {
    "strict": 0.70,
    "tolerant_1": 0.60,
    "tolerant_2": 0.50,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_results_from_model_dir(model_dir: Path) -> list[dict]:
    """Load all result JSON files from run_*/results/*.json under a model directory."""
    records: list[dict] = []
    for result_file in sorted(model_dir.glob("run_*/results/*.json")):
        try:
            records.append(json.loads(result_file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as exc:
            warnings.warn(f"{result_file}: skipping unreadable result: {exc}")
    return records


def _cup_pass_rate(records: list[dict], threshold: float) -> float:
    """Compute CuP pass rate: fraction of tasks where aggregate_score >= threshold and not hard_fail."""
    if not records:
        return 0.0
    passes = sum(
        1
        for r in records
        if not r.get("hard_fail", False)
        and r.get("aggregate_score") is not None
        and float(r["aggregate_score"]) >= threshold
    )
    return round(passes / len(records), 4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def compute_cup_threshold_ablation(runs_dir: Path) -> dict:
    """Compute CuP threshold ablation data from a runs directory."""
    variant_names = list(THRESHOLD_VARIANTS.keys())

    # Discover model subdirs (look for run_*/results/*.json)
    model_dirs: list[Path] = []
    if runs_dir.exists():
        model_dirs = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir() and any(d.glob("run_*/results/*.json"))]
        )

    if not model_dirs:
        warnings.warn(
            f"No model subdirs with run results found under {runs_dir}. "
            "Writing empty output."
        )
        return {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "variants": variant_names,
            "models": [],
            "pass_rates": {v: {} for v in variant_names},
        }

    model_names = [d.name for d in model_dirs]

    # Load records per model
    model_records: dict[str, list[dict]] = {}
    for d in model_dirs:
        model_records[d.name] = _load_results_from_model_dir(d)

    # Compute pass rates per variant × model
    pass_rates: dict[str, dict[str, float]] = {}
    for variant, threshold in THRESHOLD_VARIANTS.items():
        pass_rates[variant] = {}
        for model in model_names:
            pass_rates[variant][model] = _cup_pass_rate(model_records[model], threshold)

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "variants": variant_names,
        "models": model_names,
        "pass_rates": pass_rates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "E4 ablation: compute CuP pass rate under 3 score threshold variants "
            "(strict=0.70, tolerant_1=0.60, tolerant_2=0.50)."
        )
    )
    parser.add_argument(
        "--runs",
        default="data/runs/v02_dev/",
        help="Directory containing per-model run subdirs (default: data/runs/v02_dev/)",
    )
    parser.add_argument(
        "--output",
        default="data/ablations/cup_threshold.json",
        help="Output JSON path (default: data/ablations/cup_threshold.json)",
    )
    args = parser.parse_args(argv)

    runs_dir = Path(args.runs)
    output_path = Path(args.output)

    if not runs_dir.exists():
        warnings.warn(f"Runs directory does not exist: {runs_dir}. Writing empty output.")

    result = compute_cup_threshold_ablation(runs_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Written: {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
