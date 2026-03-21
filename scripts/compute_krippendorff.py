#!/usr/bin/env python3
"""Compute Krippendorff's alpha per rubric dimension (human annotators only).

Reads a CSV of per-rater per-dimension raw scores, computes ordinal
Krippendorff's alpha for each rubric dimension, and writes results to
data/rubric_validation/krippendorff_alpha.csv.

Usage:
    python scripts/compute_krippendorff.py --annotations PATH [--output PATH]

CSV format expected:
    response_id, rater_id, rubric_id, dimension, raw_score
    rv_job_001, human_1, hpc_job_failure_diagnosis_v1, technical_correctness, 2
    rv_job_001, human_2, hpc_job_failure_diagnosis_v1, technical_correctness, 3
    rv_job_001, human_3, hpc_job_failure_diagnosis_v1, technical_correctness, 2
    ...

Only rows where rater_id starts with 'human' are included (LLM judge excluded).
The 10 calibration responses should not be present; filter them beforehand or
mark them with calibration=True in the CSV.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import krippendorff
    import numpy as np
    import pandas as pd
except ImportError as exc:
    sys.exit(
        f"Missing dependency: {exc}\n"
        "Install with: uv add --dev krippendorff"
    )

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "rubric_validation" / "krippendorff_alpha.csv"

# Thresholds per spec §4 Gate R2
PASS_STRONG = 0.80
PASS_ADEQUATE = 0.75


def compute_alpha_for_dimension(
    df: pd.DataFrame,
    dimension: str,
    rubric_id: str,
) -> dict:
    """Compute ordinal Krippendorff alpha for a single dimension.

    Args:
        df: Filtered dataframe for one (rubric_id, dimension) combination.
            Columns: response_id, rater_id, raw_score.
        dimension: Dimension name.
        rubric_id: Rubric template identifier.

    Returns:
        Dict with alpha, pass status, and metadata.
    """
    # Build rater × item matrix (rows=raters, cols=items)
    pivot = df.pivot_table(
        index="rater_id", columns="response_id", values="raw_score", aggfunc="first"
    )
    if pivot.shape[0] < 2:
        return {
            "rubric_id": rubric_id,
            "dimension": dimension,
            "alpha": None,
            "n_raters": pivot.shape[0],
            "n_items": pivot.shape[1],
            "pass": False,
            "status": "SKIP: need ≥2 raters",
        }

    matrix = pivot.values.astype(float)
    # Replace pandas NaN with numpy nan (krippendorff handles nan as missing)
    alpha = krippendorff.alpha(matrix, level_of_measurement="ordinal")
    alpha_val = round(float(alpha), 4)

    if alpha_val >= PASS_STRONG:
        status = "PASS (strong)"
        gate_pass = True
    elif alpha_val >= PASS_ADEQUATE:
        status = "PASS with note (adequate)"
        gate_pass = True
    else:
        status = "FAIL"
        gate_pass = False

    return {
        "rubric_id": rubric_id,
        "dimension": dimension,
        "alpha": alpha_val,
        "n_raters": pivot.shape[0],
        "n_items": pivot.shape[1],
        "pass": gate_pass,
        "status": status,
    }


def main(annotations_path: str, output_path: Optional[str]) -> None:
    df = pd.read_csv(annotations_path)

    required_cols = {"response_id", "rater_id", "rubric_id", "dimension", "raw_score"}
    missing = required_cols - set(df.columns)
    if missing:
        sys.exit(f"Missing columns in annotations file: {missing}")

    # Exclude LLM judge rows
    human_df = df[df["rater_id"].str.startswith("human")]
    if human_df.empty:
        sys.exit("No rows with rater_id starting with 'human' found.")

    # Drop calibration responses if column present
    if "calibration" in human_df.columns:
        human_df = human_df[~human_df["calibration"].astype(bool)]

    results = []
    any_fail = False

    for (rubric_id, dimension), group in human_df.groupby(["rubric_id", "dimension"]):
        res = compute_alpha_for_dimension(group, str(dimension), str(rubric_id))
        results.append(res)
        alpha_str = f"{res['alpha']:.4f}" if res["alpha"] is not None else "N/A"
        print(f"  {rubric_id} / {dimension}: α={alpha_str}  → {res['status']}")
        if not res["pass"]:
            any_fail = True

    out_path = Path(output_path) if output_path else DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(out_path, index=False)
    print(f"\nResults written to {out_path}")

    if any_fail:
        failing = [r for r in results if not r["pass"] and r["alpha"] is not None]
        dims = ", ".join(f"{r['rubric_id']}/{r['dimension']}" for r in failing)
        print(f"GATE R2 FAIL: α < 0.75 for: {dims}")
        print("Trigger rubric revision for those dimensions only (see spec §5).")
        sys.exit(1)
    else:
        print("GATE R2 PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--annotations", required=True, help="Path to per-dimension annotation CSV")
    parser.add_argument("--output", default=None, help=f"Output CSV path (default: {DEFAULT_OUT})")
    args = parser.parse_args()
    main(args.annotations, args.output)
