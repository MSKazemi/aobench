#!/usr/bin/env python3
"""Compute ICC(A,1) — absolute agreement, single rater — from human annotation data.

Reads a CSV of per-rater normalized scores, computes ICC(A,1) per rubric template
and pooled across all 40 independently-annotated responses, and writes results to
data/rubric_validation/icc_results.csv.

Usage:
    python scripts/compute_icc.py --annotations PATH [--output PATH]

CSV format expected:
    response_id, rater_id, score, rubric_id
    rv_job_001, human_1, 0.75, hpc_job_failure_diagnosis_v1
    rv_job_001, human_2, 0.80, hpc_job_failure_diagnosis_v1
    ...
    rv_job_001, llm_judge, 0.78, hpc_job_failure_diagnosis_v1

The 10 calibration responses (rv_*_cal_*) are excluded automatically.
Scores must be normalized to [0, 1].
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

try:
    import pandas as pd
    import pingouin as pg
except ImportError as exc:
    sys.exit(
        f"Missing dependency: {exc}\n"
        "Install with: uv add --dev pingouin"
    )

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "rubric_validation" / "icc_results.csv"


def compute_icc(df: pd.DataFrame, label: str) -> dict:
    """Run ICC(A,1) via pingouin on a tidy dataframe.

    Args:
        df: Tidy dataframe with columns [response_id, rater_id, score].
        label: Human-readable label for the subset (e.g. template name or 'pooled').

    Returns:
        Dict with keys: label, icc_A1, ci_low, ci_high, df_between, df_error,
        df_column, n_subjects, k_raters.
    """
    icc_table = pg.intraclass_corr(
        data=df,
        targets="response_id",
        raters="rater_id",
        ratings="score",
        nan_policy="raise",
    )
    # ICC2 = two-way mixed, absolute agreement, single rater
    row = icc_table[icc_table["Type"] == "ICC2"].iloc[0]
    ci = row["CI95"]
    return {
        "label": label,
        "icc_A1": round(float(row["ICC"]), 4),
        "ci_low": round(float(ci[0]), 4),
        "ci_high": round(float(ci[1]), 4),
        "F": round(float(row["F"]), 4),
        "df1": int(row["df1"]),
        "df2": round(float(row["df2"]), 2),
        "pvalue": round(float(row["pval"]), 6),
        "n_subjects": df["response_id"].nunique(),
        "k_raters": df["rater_id"].nunique(),
        "pass": float(row["ICC"]) >= 0.80,
        "borderline": 0.70 <= float(ci[0]) < 0.80 if float(row["ICC"]) >= 0.80 else False,
    }


def main(annotations_path: str, output_path: Optional[str]) -> None:
    ann_df = pd.read_csv(annotations_path)

    required_cols = {"response_id", "rater_id", "score", "rubric_id"}
    missing = required_cols - set(ann_df.columns)
    if missing:
        sys.exit(f"Missing columns in annotations file: {missing}")

    # Drop calibration responses (if marked)
    if "calibration" in ann_df.columns:
        ann_df = ann_df[~ann_df["calibration"].astype(bool)]

    # Validate score range
    if not ((ann_df["score"] >= 0) & (ann_df["score"] <= 1)).all():
        sys.exit("Error: scores must be normalized to [0, 1].")

    results = []

    # Per-template ICC
    for rubric_id, group in ann_df.groupby("rubric_id"):
        n_responses = group["response_id"].nunique()
        n_raters = group["rater_id"].nunique()
        if n_responses < 2 or n_raters < 2:
            print(f"  SKIP {rubric_id}: need ≥2 responses and ≥2 raters (got {n_responses}r, {n_raters}a)")
            continue
        try:
            res = compute_icc(group[["response_id", "rater_id", "score"]], label=str(rubric_id))
            results.append(res)
            status = "PASS" if res["pass"] else ("BORDERLINE" if res["borderline"] else "FAIL")
            print(f"  {rubric_id}: ICC(A,1)={res['icc_A1']} "
                  f"95%CI=[{res['ci_low']}, {res['ci_high']}]  → {status}")
        except Exception as e:
            print(f"  ERROR computing ICC for {rubric_id}: {e}")

    # Pooled ICC (all templates combined)
    if ann_df["response_id"].nunique() >= 2 and ann_df["rater_id"].nunique() >= 2:
        try:
            pooled = compute_icc(
                ann_df[["response_id", "rater_id", "score"]],
                label="pooled"
            )
            results.append(pooled)
            status = "PASS" if pooled["pass"] else ("BORDERLINE" if pooled["borderline"] else "FAIL")
            print(f"\n  POOLED: ICC(A,1)={pooled['icc_A1']} "
                  f"95%CI=[{pooled['ci_low']}, {pooled['ci_high']}]  → {status}")
        except Exception as e:
            print(f"  ERROR computing pooled ICC: {e}")

    # Write CSV
    out_path = Path(output_path) if output_path else DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results_df = pd.DataFrame(results)
    results_df.to_csv(out_path, index=False)
    print(f"\nResults written to {out_path}")

    # Return non-zero exit if primary gate fails
    pooled_rows = [r for r in results if r["label"] == "pooled"]
    if pooled_rows and not pooled_rows[0]["pass"]:
        print("GATE R1 FAIL: pooled ICC(A,1) < 0.80 — trigger rubric revision protocol.")
        sys.exit(1)
    elif pooled_rows:
        print("GATE R1 PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--annotations", required=True, help="Path to annotation CSV")
    parser.add_argument("--output", default=None, help=f"Output CSV path (default: {DEFAULT_OUT})")
    args = parser.parse_args()
    main(args.annotations, args.output)
