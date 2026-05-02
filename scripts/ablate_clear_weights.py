#!/usr/bin/env python3
"""E3 ablation: sensitivity of CLEAR aggregate to dimension weight configuration.

Reads every data/runs/v02_dev/<model>/results.jsonl for all model subdirs found.
For each of 4 weight configurations, recomputes the weighted aggregate score per model.
Outputs data/ablations/clear_weights.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Weight configurations
# ---------------------------------------------------------------------------

WEIGHT_VARIANTS: dict[str, dict[str, float]] = {
    "equal": {
        "outcome": 1 / 7,
        "tool_use": 1 / 7,
        "grounding": 1 / 7,
        "governance": 1 / 7,
        "robustness": 1 / 7,
        "efficiency": 1 / 7,
        "workflow": 1 / 7,
    },
    "e_heavy": {
        "outcome": 0.40,
        "tool_use": 0.20,
        "grounding": 0.10,
        "governance": 0.15,
        "robustness": 0.05,
        "efficiency": 0.05,
        "workflow": 0.05,
    },
    "a_heavy": {
        "outcome": 0.20,
        "tool_use": 0.10,
        "grounding": 0.10,
        "governance": 0.40,
        "robustness": 0.05,
        "efficiency": 0.05,
        "workflow": 0.10,
    },
    "default": {
        "outcome": 0.30,
        "tool_use": 0.15,
        "grounding": 0.10,
        "governance": 0.20,
        "robustness": 0.10,
        "efficiency": 0.05,
        "workflow": 0.10,
    },
}

DIMENSIONS = ["outcome", "tool_use", "grounding", "governance", "robustness", "efficiency", "workflow"]


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


def _weighted_score(record: dict, weights: dict[str, float]) -> float | None:
    """Compute a weighted score for a single result record."""
    dim_scores = record.get("dimension_scores") or {}
    total_weight = 0.0
    weighted_sum = 0.0
    for dim, w in weights.items():
        val = dim_scores.get(dim)
        if val is not None:
            weighted_sum += w * float(val)
            total_weight += w
    if total_weight == 0.0:
        return None
    # Normalise so absent dimensions don't deflate the score
    return weighted_sum / total_weight


def _mean_weighted_score(records: list[dict], weights: dict[str, float]) -> float:
    """Compute mean weighted score across all records."""
    scores = [s for r in records if (s := _weighted_score(r, weights)) is not None]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Spearman rank correlation
# ---------------------------------------------------------------------------


def _rank(values: list[float]) -> list[float]:
    """Return fractional ranks (average ties) for a list of floats."""
    n = len(values)
    sorted_idx = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and values[sorted_idx[j]] == values[sorted_idx[i]]:
            j += 1
        avg_rank = (i + j - 1) / 2.0 + 1  # 1-based average rank
        for k in range(i, j):
            ranks[sorted_idx[k]] = avg_rank
        i = j
    return ranks


def _spearman_rho(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation between two equal-length lists."""
    if len(x) != len(y):
        raise ValueError("x and y must have equal length")
    n = len(x)
    if n < 2:
        return 0.0

    try:
        from scipy.stats import spearmanr  # type: ignore[import]
        import math as _math
        result = spearmanr(x, y)
        rho = float(result.statistic) if hasattr(result, "statistic") else float(result[0])
        # spearmanr returns nan when input is constant (zero variance)
        if _math.isnan(rho):
            return 0.0
        return round(rho, 4)
    except ImportError:
        pass

    # Stdlib fallback using rank correlation formula
    rx = _rank(x)
    ry = _rank(y)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_rx = (sum((v - mean_rx) ** 2 for v in rx) ** 0.5)
    std_ry = (sum((v - mean_ry) ** 2 for v in ry) ** 0.5)
    if std_rx == 0.0 or std_ry == 0.0:
        return 0.0
    return round(cov / (std_rx * std_ry), 4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def compute_clear_weights_ablation(runs_dir: Path) -> dict:
    """Compute CLEAR weight ablation data from a runs directory."""
    variant_names = list(WEIGHT_VARIANTS.keys())

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
            "scores": {v: {} for v in variant_names},
            "spearman_rho": {
                "equal_vs_default": 0.0,
                "e_heavy_vs_default": 0.0,
                "a_heavy_vs_default": 0.0,
            },
        }

    model_names = [d.name for d in model_dirs]

    # Load records per model
    model_records: dict[str, list[dict]] = {}
    for d in model_dirs:
        model_records[d.name] = _load_results_from_model_dir(d)

    # Compute scores per variant × model
    scores: dict[str, dict[str, float]] = {}
    for variant, weights in WEIGHT_VARIANTS.items():
        scores[variant] = {}
        for model in model_names:
            scores[variant][model] = round(
                _mean_weighted_score(model_records[model], weights), 4
            )

    # Pairwise Spearman rho: compare variant rankings across models
    def _scores_vector(variant: str) -> list[float]:
        return [scores[variant][m] for m in model_names]

    spearman_rho: dict[str, float] = {}
    for other in ("equal", "e_heavy", "a_heavy"):
        key = f"{other}_vs_default"
        spearman_rho[key] = _spearman_rho(
            _scores_vector(other), _scores_vector("default")
        )

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "variants": variant_names,
        "models": model_names,
        "scores": scores,
        "spearman_rho": spearman_rho,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "E3 ablation: recompute CLEAR aggregate under 4 weight configurations "
            "and report pairwise Spearman rank correlations."
        )
    )
    parser.add_argument(
        "--runs",
        default="data/runs/v02_dev/",
        help="Directory containing per-model run subdirs (default: data/runs/v02_dev/)",
    )
    parser.add_argument(
        "--output",
        default="data/ablations/clear_weights.json",
        help="Output JSON path (default: data/ablations/clear_weights.json)",
    )
    args = parser.parse_args(argv)

    runs_dir = Path(args.runs)
    output_path = Path(args.output)

    if not runs_dir.exists():
        warnings.warn(f"Runs directory does not exist: {runs_dir}. Writing empty output.")

    result = compute_clear_weights_ablation(runs_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Written: {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
