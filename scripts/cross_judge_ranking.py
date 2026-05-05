#!/usr/bin/env python3
"""Cross-judge ranking consistency check (Gate R4): Kendall τ_b ≥ 0.90.

Scores all 50 validation responses with two judge models and reports the
Kendall tau-b rank correlation between their score vectors.

Usage:
    python scripts/cross_judge_ranking.py \\
        --responses data/rubric_validation/responses/ \\
        --primary-judge gemini-2.5-flash \\
        --secondary-judge gpt-4.1 \\
        --output data/rubric_validation/cross_judge_ranking.csv

Gate thresholds (spec §4 Gate R4):
    PASS:       τ_b >= 0.90
    BORDERLINE: 0.80 <= τ_b < 0.90  (report both judges in paper)
    FAIL:       τ_b < 0.80           (rubric prompt is ambiguous)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_RESPONSES_DIR = ROOT / "data" / "rubric_validation" / "responses"
DEFAULT_OUT = ROOT / "data" / "rubric_validation" / "cross_judge_ranking.csv"


def load_all_responses(responses_dir: Path) -> list[dict]:
    paths = sorted(responses_dir.glob("rv_*.json"))
    if not paths:
        sys.exit(f"No rv_*.json files found in {responses_dir}")
    responses = []
    for p in paths:
        with open(p) as f:
            responses.append(json.load(f))
    return responses


def call_judge(response: dict, judge_model: str) -> float:
    """Call the rubric judge and return normalized score [0, 1].

    Set EXABENCH_DRY_RUN=1 for synthetic scores (testing).
    """
    if os.environ.get("EXABENCH_DRY_RUN") == "1":
        import hashlib
        import random
        # Use response_id as the primary seed so both judges produce correlated rankings.
        # A small per-judge offset ensures scores are not identical without disrupting order.
        seed_str = response["response_id"]
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        tier = response.get("quality_tier", "moderate")
        base = {"poor": 0.15, "moderate": 0.50, "good": 0.82}[tier]
        judge_offset = 0.02 if "gemini" in judge_model else -0.02
        return round(min(1.0, max(0.0, base + rng.uniform(-0.03, 0.03) + judge_offset)), 4)

    try:
        from aobench.scoring.rubric_scorer import RubricScorer  # type: ignore[import]
    except ImportError:
        sys.exit(
            "Cannot import aobench.scoring.rubric_scorer. "
            "Run from project root with 'uv run' or set EXABENCH_DRY_RUN=1."
        )

    scorer = RubricScorer(model=judge_model)
    result = scorer.score(
        task_context=response["task_context"],
        task_question=response["task_question"],
        agent_response=response["agent_response"],
        rubric_id=response["rubric_id"],
    )
    return result.normalized_score


def main(
    responses_dir: str,
    primary_judge: str,
    secondary_judge: str,
    output_path: Optional[str],
) -> None:
    from scipy.stats import kendalltau  # type: ignore[import]

    rdir = Path(responses_dir)
    responses = load_all_responses(rdir)
    n = len(responses)
    print(f"  Scoring {n} responses with primary judge: {primary_judge}")

    primary_scores = []
    secondary_scores = []
    rows = []

    for i, resp in enumerate(responses):
        rid = resp["response_id"]
        print(f"  [{i+1}/{n}] {rid}...", flush=True)

        p_score = call_judge(resp, primary_judge)
        s_score = call_judge(resp, secondary_judge)
        primary_scores.append(p_score)
        secondary_scores.append(s_score)

        rows.append({
            "response_id": rid,
            "rubric_id": resp["rubric_id"],
            "quality_tier": resp.get("quality_tier", ""),
            f"score_{primary_judge.replace('-', '_').replace('.', '_')}": p_score,
            f"score_{secondary_judge.replace('-', '_').replace('.', '_')}": s_score,
        })

    tau, p_value = kendalltau(primary_scores, secondary_scores)
    tau = round(float(tau), 4)
    p_value = round(float(p_value), 6)

    print(f"\n  Kendall τ_b = {tau:.4f} (p={p_value:.6f})")
    print(f"  Primary   mean score: {sum(primary_scores)/len(primary_scores):.4f}")
    print(f"  Secondary mean score: {sum(secondary_scores)/len(secondary_scores):.4f}")

    if tau >= 0.90:
        status = "PASS"
    elif tau >= 0.80:
        status = "BORDERLINE — report both judges in paper"
    else:
        status = "FAIL — investigate rubric prompt for ambiguity"
    print(f"\nGATE R4 {status}")

    # Write CSV
    out_path = Path(output_path) if output_path else DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Append summary
    with open(out_path, "a", newline="") as f:
        writer_r = csv.writer(f)
        writer_r.writerow([])
        writer_r.writerow(["SUMMARY", "kendall_tau_b", tau, "pvalue", p_value, "gate", status])

    print(f"Results written to {out_path}")

    if tau < 0.80:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--responses",
        default=str(DEFAULT_RESPONSES_DIR),
        help="Directory containing rv_*.json response files",
    )
    parser.add_argument(
        "--primary-judge",
        default="gemini-2.5-flash",
        help="Primary judge model (default: gemini-2.5-flash)",
    )
    parser.add_argument(
        "--secondary-judge",
        default="gpt-4.1",
        help="Secondary judge model (default: gpt-4.1)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=f"Output CSV path (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()
    main(args.responses, args.primary_judge, args.secondary_judge, args.output)
