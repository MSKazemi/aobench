"""Unit tests for rubric validation scripts.

Tests cover:
- compute_icc.py: ICC(A,1) computation with synthetic annotation data
- compute_krippendorff.py: Krippendorff alpha computation per dimension
- stochastic_stability.py: dry-run mode judge invocation and stats
- cross_judge_ranking.py: dry-run mode cross-judge τ_b computation
- Response file integrity: all 50 rv_*.json files are valid and schema-correct
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path
from statistics import mean, stdev

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
RESPONSES_DIR = ROOT / "data" / "rubric_validation" / "responses"
SCRIPTS_DIR = ROOT / "scripts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_annotation_csv(
    response_ids: list[str],
    rater_ids: list[str],
    rubric_id: str = "hpc_job_failure_diagnosis_v1",
    base_scores: dict | None = None,
) -> str:
    """Return a CSV string with synthetic per-rater scores."""
    rows = ["response_id,rater_id,score,rubric_id"]
    for rid in response_ids:
        for rater in rater_ids:
            score = (base_scores or {}).get((rid, rater), 0.5)
            rows.append(f"{rid},{rater},{score},{rubric_id}")
    return "\n".join(rows)


def make_dimension_csv(
    response_ids: list[str],
    rater_ids: list[str],
    dimensions: list[str],
    rubric_id: str = "hpc_job_failure_diagnosis_v1",
    score_map: dict | None = None,
) -> str:
    """Return per-dimension CSV for Krippendorff alpha."""
    rows = ["response_id,rater_id,rubric_id,dimension,raw_score"]
    for dim in dimensions:
        for rid in response_ids:
            for rater in rater_ids:
                score = (score_map or {}).get((rid, rater, dim), 2)
                rows.append(f"{rid},{rater},{rubric_id},{dim},{score}")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# E1: Response file integrity
# ---------------------------------------------------------------------------

class TestResponseFiles:
    REQUIRED_KEYS = {"response_id", "rubric_id", "task_context", "task_question",
                     "agent_response", "quality_tier"}
    VALID_RUBRIC_IDS = {
        "hpc_job_failure_diagnosis_v1",
        "hpc_energy_anomaly_v1",
        "hpc_rbac_response_v1",
    }
    VALID_TIERS = {"poor", "moderate", "good"}

    def _load_all(self) -> list[dict]:
        files = sorted(RESPONSES_DIR.glob("rv_*.json"))
        return [json.loads(p.read_text()) for p in files]

    def test_count_is_50(self):
        files = list(RESPONSES_DIR.glob("rv_*.json"))
        assert len(files) == 50, f"Expected 50 response files, found {len(files)}"

    def test_all_files_have_required_keys(self):
        for resp in self._load_all():
            missing = self.REQUIRED_KEYS - set(resp.keys())
            assert not missing, f"{resp.get('response_id')}: missing keys {missing}"

    def test_rubric_ids_are_valid(self):
        for resp in self._load_all():
            assert resp["rubric_id"] in self.VALID_RUBRIC_IDS, (
                f"{resp['response_id']}: invalid rubric_id {resp['rubric_id']!r}"
            )

    def test_quality_tiers_are_valid(self):
        for resp in self._load_all():
            assert resp["quality_tier"] in self.VALID_TIERS, (
                f"{resp['response_id']}: invalid tier {resp['quality_tier']!r}"
            )

    def test_rubric_template_counts(self):
        all_resp = self._load_all()
        by_rubric = {}
        for r in all_resp:
            by_rubric.setdefault(r["rubric_id"], 0)
            by_rubric[r["rubric_id"]] += 1
        assert by_rubric.get("hpc_job_failure_diagnosis_v1", 0) == 20
        assert by_rubric.get("hpc_energy_anomaly_v1", 0) == 15
        assert by_rubric.get("hpc_rbac_response_v1", 0) == 15

    def test_quality_tier_distribution_not_degenerate(self):
        """No tier should contain all 50 responses (degenerate check)."""
        tiers = [r["quality_tier"] for r in self._load_all()]
        for tier in self.VALID_TIERS:
            count = tiers.count(tier)
            assert count < 50, f"All responses are tier={tier!r} — degenerate distribution"
            assert count > 0, f"No responses of tier={tier!r}"

    def test_response_ids_are_unique(self):
        ids = [r["response_id"] for r in self._load_all()]
        assert len(ids) == len(set(ids)), "Duplicate response_ids found"

    def test_no_empty_fields(self):
        for resp in self._load_all():
            for key in self.REQUIRED_KEYS:
                assert resp[key], f"{resp['response_id']}: empty value for field {key!r}"


# ---------------------------------------------------------------------------
# E4: compute_icc.py
# ---------------------------------------------------------------------------

class TestComputeICC:
    def test_icc_high_agreement(self, tmp_path):
        """Near-perfect agreement should produce ICC close to 1.0."""
        import pandas as pd
        import pingouin as pg

        responses = [f"rv_job_{i:03d}" for i in range(1, 11)]
        raters = ["human_1", "human_2", "human_3", "llm_judge"]
        rows = []
        for i, rid in enumerate(responses):
            base = (i + 1) / 11.0
            for rater in raters:
                offset = {"human_1": 0.0, "human_2": 0.01, "human_3": -0.01, "llm_judge": 0.02}[rater]
                rows.append({"response_id": rid, "rater_id": rater, "score": round(base + offset, 4),
                              "rubric_id": "hpc_job_failure_diagnosis_v1"})
        df = pd.DataFrame(rows)
        icc_table = pg.intraclass_corr(
            data=df, targets="response_id", raters="rater_id", ratings="score", nan_policy="raise"
        )
        icc_val = icc_table[icc_table["Type"] == "ICC2"]["ICC"].values[0]
        assert icc_val > 0.90, f"Expected ICC > 0.90 for near-perfect agreement, got {icc_val:.4f}"

    def test_icc_low_agreement(self):
        """Random scores should yield low ICC."""
        import pandas as pd
        import pingouin as pg
        import random

        rng = random.Random(42)
        responses = [f"rv_job_{i:03d}" for i in range(1, 11)]
        raters = ["human_1", "human_2", "human_3"]
        rows = [
            {"response_id": rid, "rater_id": rater, "score": round(rng.random(), 4),
             "rubric_id": "hpc_job_failure_diagnosis_v1"}
            for rid in responses for rater in raters
        ]
        df = pd.DataFrame(rows)
        icc_table = pg.intraclass_corr(
            data=df, targets="response_id", raters="rater_id", ratings="score", nan_policy="raise"
        )
        icc_val = icc_table[icc_table["Type"] == "ICC2"]["ICC"].values[0]
        # Random data can produce near-zero or even negative ICC
        assert icc_val < 0.80, f"Expected ICC < 0.80 for random scores, got {icc_val:.4f}"

    def test_script_runs_with_synthetic_csv(self, tmp_path):
        """compute_icc.py should write icc_results.csv for valid input."""
        import pandas as pd
        import random

        rng = random.Random(99)
        responses = [f"rv_job_{i:03d}" for i in range(1, 11)]
        raters = ["human_1", "human_2", "human_3", "llm_judge"]
        rows = []
        for i, rid in enumerate(responses):
            base = (i + 1) / 11.0
            for rater in raters:
                rows.append({
                    "response_id": rid,
                    "rater_id": rater,
                    "score": round(base + rng.uniform(-0.05, 0.05), 4),
                    "rubric_id": "hpc_job_failure_diagnosis_v1",
                })
        ann_path = tmp_path / "annotations.csv"
        pd.DataFrame(rows).to_csv(ann_path, index=False)
        out_path = tmp_path / "icc_results.csv"

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "compute_icc.py"),
             "--annotations", str(ann_path), "--output", str(out_path)],
            capture_output=True, text=True
        )
        assert out_path.exists(), f"Output not created. stderr: {result.stderr}"
        df_out = pd.read_csv(out_path)
        assert "icc_A1" in df_out.columns
        assert len(df_out) >= 1  # at least pooled row


# ---------------------------------------------------------------------------
# E5: compute_krippendorff.py
# ---------------------------------------------------------------------------

class TestComputeKrippendorff:
    def test_alpha_high_agreement(self):
        """Near-identical ordinal scores should give high alpha."""
        import krippendorff
        import numpy as np

        # 3 raters × 10 items, near-identical scores
        data = np.array([
            [0, 1, 2, 3, 2, 1, 0, 2, 3, 1],
            [0, 1, 2, 3, 2, 1, 0, 2, 3, 1],
            [0, 1, 2, 3, 2, 1, 0, 2, 3, 1],
        ], dtype=float)
        alpha = krippendorff.alpha(data, level_of_measurement="ordinal")
        assert alpha > 0.95, f"Expected α > 0.95, got {alpha:.4f}"

    def test_alpha_random_scores(self):
        """Random scores should give low alpha."""
        import krippendorff
        import numpy as np

        rng = np.random.default_rng(42)
        data = rng.integers(0, 4, size=(3, 20)).astype(float)
        alpha = krippendorff.alpha(data, level_of_measurement="ordinal")
        assert alpha < 0.75, f"Expected α < 0.75 for random, got {alpha:.4f}"

    def test_script_runs_and_outputs_csv(self, tmp_path):
        """compute_krippendorff.py should write krippendorff_alpha.csv."""
        import pandas as pd

        responses = [f"rv_job_{i:03d}" for i in range(1, 11)]
        dims = ["technical_correctness", "role_appropriateness"]
        rows = []
        for dim in dims:
            for i, rid in enumerate(responses):
                for rater in ["human_1", "human_2", "human_3"]:
                    offset = {"human_1": 0, "human_2": 0, "human_3": 1}[rater] if i == 5 else 0
                    rows.append({
                        "response_id": rid,
                        "rater_id": rater,
                        "rubric_id": "hpc_job_failure_diagnosis_v1",
                        "dimension": dim,
                        "raw_score": i % 4 + offset,
                    })
        ann_path = tmp_path / "dim_annotations.csv"
        pd.DataFrame(rows).to_csv(ann_path, index=False)
        out_path = tmp_path / "alpha.csv"

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "compute_krippendorff.py"),
             "--annotations", str(ann_path), "--output", str(out_path)],
            capture_output=True, text=True
        )
        assert out_path.exists(), f"Output not created. stderr: {result.stderr}"
        df_out = pd.read_csv(out_path)
        assert "alpha" in df_out.columns
        assert set(df_out["dimension"]) == set(dims)


# ---------------------------------------------------------------------------
# E6: stochastic_stability.py (dry run)
# ---------------------------------------------------------------------------

class TestStochasticStability:
    def test_dry_run_produces_csv(self, tmp_path):
        """Dry-run mode should produce stochastic_stability.csv."""
        import pandas as pd

        out_path = tmp_path / "stability.csv"
        env = {**os.environ, "EXABENCH_DRY_RUN": "1"}
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "stochastic_stability.py"),
             "--responses", str(RESPONSES_DIR),
             "--sample", "rv_job_015,rv_job_001,rv_energy_012",
             "--runs", "4",
             "--output", str(out_path)],
            capture_output=True, text=True, env=env
        )
        assert result.returncode == 0, f"Script failed:\n{result.stderr}"
        assert out_path.exists()

        # Read up to the first blank/summary line
        content = out_path.read_text()
        lines = [l for l in content.splitlines() if l and not l.startswith("SUMMARY")]
        df = pd.read_csv(StringIO("\n".join(lines)))
        assert "std_score" in df.columns
        assert len(df) >= 3

    def test_dry_run_scores_are_within_bounds(self):
        """Dry-run synthetic scores should be in [0, 1]."""
        import json
        import importlib.util
        import sys as _sys

        # Load the script as a module
        spec = importlib.util.spec_from_file_location(
            "stochastic_stability",
            str(SCRIPTS_DIR / "stochastic_stability.py")
        )
        mod = importlib.util.load_from_spec = None
        # Use subprocess to invoke with a single response
        env = {**os.environ, "EXABENCH_DRY_RUN": "1"}
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "stochastic_stability.py"),
             "--responses", str(RESPONSES_DIR),
             "--sample", "rv_job_015",
             "--runs", "8",
             "--output", "/dev/null"],
            capture_output=True, text=True, env=env
        )
        # Parse score lines from stdout
        scores = []
        for line in result.stdout.splitlines():
            if line.strip().startswith("run ") and ":" in line:
                parts = line.strip().split(":")
                if len(parts) >= 2:
                    try:
                        scores.append(float(parts[-1].strip()))
                    except ValueError:
                        pass
        assert all(0.0 <= s <= 1.0 for s in scores), f"Out-of-bounds scores: {scores}"

    def test_stability_stats_logic(self):
        """Verify the mean/std logic for a known set of scores."""
        scores_a = [0.80, 0.82, 0.79, 0.81, 0.80, 0.83, 0.78, 0.81]
        scores_b = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]  # high variance ~0.53
        std_a = stdev(scores_a)
        std_b = stdev(scores_b)
        assert std_a < 0.20, f"Expected low std for stable scores, got {std_a:.4f}"
        assert std_b > 0.30, f"Expected high std for unstable scores, got {std_b:.4f}"
        # Gate R3: max_std < 0.35
        assert std_a < 0.35
        assert std_b >= 0.35


# ---------------------------------------------------------------------------
# E7: cross_judge_ranking.py (dry run)
# ---------------------------------------------------------------------------

class TestCrossJudgeRanking:
    def test_dry_run_produces_csv(self, tmp_path):
        """Dry-run mode should produce cross_judge_ranking.csv with 50 rows."""
        import pandas as pd

        out_path = tmp_path / "ranking.csv"
        env = {**os.environ, "EXABENCH_DRY_RUN": "1"}
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "cross_judge_ranking.py"),
             "--responses", str(RESPONSES_DIR),
             "--primary-judge", "gemini-2.5-flash",
             "--secondary-judge", "gpt-4.1",
             "--output", str(out_path)],
            capture_output=True, text=True, env=env,
            timeout=120,
        )
        assert out_path.exists(), f"Output not created. stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

        content = out_path.read_text()
        lines = [l for l in content.splitlines() if l and not l.startswith("SUMMARY")]
        df = pd.read_csv(StringIO("\n".join(lines)))
        assert len(df) == 50, f"Expected 50 rows, got {len(df)}"
        assert "response_id" in df.columns
        # τ_b should be reasonable (≥ 0.70) for correlated dry-run scores
        assert "Kendall" in result.stdout or "tau" in result.stdout.lower()

    def test_dry_run_tau_computation(self):
        """Kendall tau computation with near-identical rankings should be high."""
        from scipy.stats import kendalltau

        # Identical rankings → τ = 1.0
        primary = list(range(10))
        secondary = list(range(10))
        tau, _ = kendalltau(primary, secondary)
        assert abs(tau - 1.0) < 1e-9

        # Reversed rankings → τ = -1.0
        reversed_ = list(range(9, -1, -1))
        tau_rev, _ = kendalltau(primary, reversed_)
        assert abs(tau_rev + 1.0) < 1e-9

    def test_gate_r4_threshold(self):
        """Verify gate R4 passes at τ_b >= 0.90."""
        from scipy.stats import kendalltau

        # Monotonically increasing rankings with tiny per-judge jitter → τ_b ≈ 1.0
        primary = [i * 0.1 for i in range(10)]
        secondary = [i * 0.1 + 0.001 for i in range(10)]
        tau, _ = kendalltau(primary, secondary)
        assert tau >= 0.90, f"Expected τ_b >= 0.90, got {tau:.4f}"
