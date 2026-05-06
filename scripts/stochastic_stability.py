#!/usr/bin/env python3
"""Measure stochastic stability of the LLM judge (Gate R3).

Runs the judge 8 times on each of 10 selected validation responses and
reports per-response mean and standard deviation of the normalized total score.

Usage:
    python scripts/stochastic_stability.py \\
        --responses data/rubric_validation/responses/ \\
        --sample rv_job_015,rv_job_007,rv_job_001,rv_energy_012,rv_energy_006,rv_energy_001,rv_rbac_011,rv_rbac_005,rv_rbac_001,rv_job_016 \\
        --judge-model gemini-2.5-flash \\
        --runs 8 \\
        --output data/rubric_validation/stochastic_stability.csv

The judge is called via the aobench RubricScorer interface.  Set
JUDGE_API_KEY / JUDGE_PROVIDER env vars before running.

Gate thresholds (spec §4 Gate R3):
    PASS:       max_std < 0.35 AND mean_std < 0.20
    BORDERLINE: max_std < 0.35 AND mean_std >= 0.20
    FAIL:       max_std >= 0.35 for any response
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from statistics import mean, stdev
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_RESPONSES_DIR = ROOT / "data" / "rubric_validation" / "responses"
DEFAULT_OUT = ROOT / "data" / "rubric_validation" / "stochastic_stability.csv"

# Default 10-response sample: 2-3 per quality tier, all 3 templates
DEFAULT_SAMPLE = [
    "rv_job_015",    # good
    "rv_job_007",    # moderate
    "rv_job_001",    # poor
    "rv_energy_012", # good
    "rv_energy_006", # moderate
    "rv_energy_001", # poor
    "rv_rbac_011",   # good
    "rv_rbac_005",   # moderate
    "rv_rbac_001",   # poor
    "rv_job_016",    # good (second good sample)
]


def load_response(responses_dir: Path, response_id: str) -> dict:
    path = responses_dir / f"{response_id}.json"
    if not path.exists():
        sys.exit(f"Response file not found: {path}")
    with open(path) as f:
        return json.load(f)


def call_judge(response: dict, judge_model: str) -> float:
    """Call the rubric judge and return the normalized total score [0, 1].

    This integrates with the AOBench RubricScorer.  When AOBENCH_DRY_RUN=1
    is set, returns a synthetic score for testing.
    """
    if os.environ.get("AOBENCH_DRY_RUN") == "1":
        # Deterministic-ish synthetic scores for testing
        import hashlib
        import random
        seed_str = response["response_id"] + str(time.time_ns() % 1000)
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        tier = response.get("quality_tier", "moderate")
        base = {"poor": 0.15, "moderate": 0.50, "good": 0.82}[tier]
        return round(min(1.0, max(0.0, base + rng.uniform(-0.12, 0.12))), 4)

    try:
        from aobench.scoring.rubric_scorer import RubricScorer  # type: ignore[import]
    except ImportError:
        sys.exit(
            "Cannot import aobench.scoring.rubric_scorer. "
            "Run from the project root with 'uv run' or set AOBENCH_DRY_RUN=1 for a dry run."
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
    sample: list[str],
    judge_model: str,
    n_runs: int,
    output_path: Optional[str],
) -> None:
    rdir = Path(responses_dir)
    results = {}

    for response_id in sample:
        response = load_response(rdir, response_id)
        print(f"  Scoring {response_id} ({n_runs} runs)...", flush=True)
        scores = []
        for i in range(n_runs):
            score = call_judge(response, judge_model)
            scores.append(score)
            print(f"    run {i+1}/{n_runs}: {score:.4f}", flush=True)

        mu = round(mean(scores), 4)
        sigma = round(stdev(scores) if len(scores) > 1 else 0.0, 4)
        results[response_id] = {
            "response_id": response_id,
            "rubric_id": response["rubric_id"],
            "quality_tier": response.get("quality_tier", ""),
            "mean_score": mu,
            "std_score": sigma,
            "runs": n_runs,
            "scores": scores,
        }
        print(f"    → mean={mu}, std={sigma}")

    max_std = max(r["std_score"] for r in results.values())
    mean_std = round(mean(r["std_score"] for r in results.values()), 4)

    print(f"\n  Summary: max_std={max_std:.4f}, mean_std={mean_std:.4f}")

    if max_std < 0.35 and mean_std < 0.20:
        print("GATE R3 PASS")
    elif max_std < 0.35:
        print("GATE R3 BORDERLINE — mean_std >= 0.20; report in paper")
    else:
        worst = max(results.values(), key=lambda r: r["std_score"])
        print(f"GATE R3 FAIL — {worst['response_id']} std={worst['std_score']:.4f} >= 0.35")
        print("Consider lowering temperature, switching judge model, or enforcing JSON output mode.")

    # Write CSV
    out_path = Path(output_path) if output_path else DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["response_id", "rubric_id", "quality_tier", "mean_score", "std_score", "runs"],
        )
        writer.writeheader()
        for r in results.values():
            writer.writerow({k: r[k] for k in writer.fieldnames})

    # Append summary row
    with open(out_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([])
        writer.writerow(["SUMMARY", "", "", mean_std, max_std, n_runs])

    print(f"Results written to {out_path}")

    if max_std >= 0.35:
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
        "--sample",
        default=",".join(DEFAULT_SAMPLE),
        help="Comma-separated list of response_ids to score (default: 10 balanced sample)",
    )
    parser.add_argument(
        "--judge-model",
        default="gemini-2.5-flash",
        help="Judge model identifier (default: gemini-2.5-flash)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=8,
        help="Number of judge invocations per response (default: 8)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=f"Output CSV path (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()
    sample = [s.strip() for s in args.sample.split(",") if s.strip()]
    main(args.responses, sample, args.judge_model, args.runs, args.output)
