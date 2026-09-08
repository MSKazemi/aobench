"""Tests for E3/E4/E5 ablation post-processing scripts.

Writes synthetic per-task result files under the ``<model>/run_*/results/*.json``
layout that the ablation scripts discover (the same layout ``TraceWriter``
produces), with 10 tasks per model (2 models) covering easy/medium/hard
difficulties, scores 0.0–1.0, and some hard_fail=True entries.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

_TS = "2026-01-01T00:00:00+00:00"

# 10 synthetic tasks: mix of difficulties, scores, and hard_fail flags
_SYNTHETIC_TASKS = [
    # (task_id, difficulty, aggregate_score, hard_fail, dim_scores)
    ("TASK_001", "easy",   0.90, False, {"outcome": 0.90, "tool_use": 0.85, "grounding": 0.80,
                                          "governance": 0.95, "robustness": 0.80, "efficiency": 0.75, "workflow": 0.80}),
    ("TASK_002", "easy",   0.75, False, {"outcome": 0.75, "tool_use": 0.70, "grounding": 0.65,
                                          "governance": 0.80, "robustness": 0.70, "efficiency": 0.60, "workflow": 0.65}),
    ("TASK_003", "easy",   0.30, True,  {"outcome": 0.30, "tool_use": 0.20, "grounding": 0.25,
                                          "governance": 0.50, "robustness": 0.30, "efficiency": 0.20, "workflow": 0.25}),
    ("TASK_004", "medium", 0.60, False, {"outcome": 0.60, "tool_use": 0.55, "grounding": 0.50,
                                          "governance": 0.65, "robustness": 0.55, "efficiency": 0.50, "workflow": 0.55}),
    ("TASK_005", "medium", 0.45, False, {"outcome": 0.45, "tool_use": 0.40, "grounding": 0.35,
                                          "governance": 0.50, "robustness": 0.45, "efficiency": 0.40, "workflow": 0.40}),
    ("TASK_006", "medium", 0.80, False, {"outcome": 0.80, "tool_use": 0.75, "grounding": 0.70,
                                          "governance": 0.85, "robustness": 0.75, "efficiency": 0.65, "workflow": 0.70}),
    ("TASK_007", "medium", 0.10, True,  {"outcome": 0.10, "tool_use": 0.05, "grounding": 0.10,
                                          "governance": 0.20, "robustness": 0.10, "efficiency": 0.05, "workflow": 0.10}),
    ("TASK_008", "hard",   0.50, False, {"outcome": 0.50, "tool_use": 0.45, "grounding": 0.40,
                                          "governance": 0.55, "robustness": 0.50, "efficiency": 0.45, "workflow": 0.45}),
    ("TASK_009", "hard",   0.20, False, {"outcome": 0.20, "tool_use": 0.15, "grounding": 0.20,
                                          "governance": 0.25, "robustness": 0.20, "efficiency": 0.15, "workflow": 0.20}),
    ("TASK_010", "hard",   0.65, False, {"outcome": 0.65, "tool_use": 0.60, "grounding": 0.55,
                                          "governance": 0.70, "robustness": 0.65, "efficiency": 0.55, "workflow": 0.60}),
]


def _make_result_record(
    task_id: str,
    difficulty: str,
    aggregate_score: float,
    hard_fail: bool,
    dim_scores: dict,
    model: str,
    run_idx: int,
) -> dict:
    return {
        "result_id": f"r_{model}_{task_id}",
        "run_id": f"run_{model}_001",
        "task_id": task_id,
        "role": "sysadmin",
        "environment_id": "env_01",
        "adapter_name": "test_adapter",
        "model_name": model,
        "hard_fail": hard_fail,
        "hard_fail_reason": "score below threshold" if hard_fail else None,
        "rbac_compliant": True,
        "dimension_scores": dim_scores,
        "aggregate_score": aggregate_score,
        "difficulty": difficulty,
        "task_difficulty_tier": {"easy": 1, "medium": 2, "hard": 3}[difficulty],
        "weight_profile_name": "default_hpc_v01",
        "timestamp": _TS,
    }


def _write_model_results(
    model_dir: Path, records: list[dict], run_name: str = "run_synth"
) -> None:
    """Write each record as an individual ``run_*/results/<task>_result.json`` file.

    This mirrors the on-disk layout ``TraceWriter`` produces and that the ablation
    scripts discover via ``glob("run_*/results/*.json")``. The run subdir name must
    start with ``run_`` for the scripts' glob to match it.
    """
    results_dir = model_dir / run_name / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        stem = rec.get("task_id") or rec.get("result_id") or "record"
        (results_dir / f"{stem}_result.json").write_text(json.dumps(rec), encoding="utf-8")


def _write_synthetic_runs(tmp_path: Path, models: list[str] | None = None) -> Path:
    """Write synthetic per-task result files for each model under tmp_path/v02_dev/."""
    if models is None:
        models = ["model_alpha", "model_beta"]

    runs_dir = tmp_path / "v02_dev"
    for idx, model in enumerate(models):
        records = [
            _make_result_record(*task, model=model, run_idx=idx)
            for task in _SYNTHETIC_TASKS
        ]
        _write_model_results(runs_dir / model, records)
    return runs_dir


# ---------------------------------------------------------------------------
# Import scripts under test
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"


def _import_script(name: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def ablate_clear_weights():
    return _import_script("ablate_clear_weights")


@pytest.fixture(scope="module")
def ablate_cup_threshold():
    return _import_script("ablate_cup_threshold")


@pytest.fixture(scope="module")
def ablate_difficulty():
    return _import_script("ablate_difficulty")


# ---------------------------------------------------------------------------
# E3: clear_weights tests
# ---------------------------------------------------------------------------


class TestAbleateClearWeights:
    def test_output_file_created(self, tmp_path, ablate_clear_weights):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "clear_weights.json"
        ret = ablate_clear_weights.main(["--runs", str(runs_dir), "--output", str(out)])
        assert ret == 0
        assert out.exists()

    def test_output_valid_json(self, tmp_path, ablate_clear_weights):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "clear_weights.json"
        ablate_clear_weights.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_schema_keys(self, tmp_path, ablate_clear_weights):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "clear_weights.json"
        ablate_clear_weights.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "generated_at" in data
        assert "variants" in data
        assert "models" in data
        assert "scores" in data
        assert "spearman_rho" in data

    def test_variants_present(self, tmp_path, ablate_clear_weights):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "clear_weights.json"
        ablate_clear_weights.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert set(data["variants"]) == {"equal", "e_heavy", "a_heavy", "default"}

    def test_models_detected(self, tmp_path, ablate_clear_weights):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "clear_weights.json"
        ablate_clear_weights.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert set(data["models"]) == {"model_alpha", "model_beta"}

    def test_scores_in_range(self, tmp_path, ablate_clear_weights):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "clear_weights.json"
        ablate_clear_weights.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        for variant, model_scores in data["scores"].items():
            for model, score in model_scores.items():
                assert 0.0 <= score <= 1.0, (
                    f"Score out of range for variant={variant}, model={model}: {score}"
                )

    def test_spearman_rho_keys(self, tmp_path, ablate_clear_weights):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "clear_weights.json"
        ablate_clear_weights.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        rho = data["spearman_rho"]
        assert set(rho.keys()) == {"equal_vs_default", "e_heavy_vs_default", "a_heavy_vs_default"}

    def test_spearman_rho_range(self, tmp_path, ablate_clear_weights):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "clear_weights.json"
        ablate_clear_weights.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        for key, rho in data["spearman_rho"].items():
            assert -1.0 <= rho <= 1.0, f"Spearman rho out of [-1, 1] for {key}: {rho}"

    def test_empty_runs_dir_no_crash(self, tmp_path, ablate_clear_weights):
        """Non-existent runs dir should produce valid JSON with empty models."""
        out = tmp_path / "clear_weights_empty.json"
        ret = ablate_clear_weights.main([
            "--runs", str(tmp_path / "nonexistent"),
            "--output", str(out),
        ])
        assert ret == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["models"] == []
        assert all(v == {} for v in data["scores"].values())

    def test_empty_runs_dir_schema_intact(self, tmp_path, ablate_clear_weights):
        out = tmp_path / "cw_empty.json"
        ablate_clear_weights.main([
            "--runs", str(tmp_path / "no_such_dir"),
            "--output", str(out),
        ])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "spearman_rho" in data
        assert set(data["spearman_rho"].keys()) == {
            "equal_vs_default", "e_heavy_vs_default", "a_heavy_vs_default"
        }


# ---------------------------------------------------------------------------
# E4: cup_threshold tests
# ---------------------------------------------------------------------------


class TestAblateCupThreshold:
    def test_output_file_created(self, tmp_path, ablate_cup_threshold):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "cup_threshold.json"
        ret = ablate_cup_threshold.main(["--runs", str(runs_dir), "--output", str(out)])
        assert ret == 0
        assert out.exists()

    def test_output_valid_json(self, tmp_path, ablate_cup_threshold):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "cup_threshold.json"
        ablate_cup_threshold.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_schema_keys(self, tmp_path, ablate_cup_threshold):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "cup_threshold.json"
        ablate_cup_threshold.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "generated_at" in data
        assert "variants" in data
        assert "models" in data
        assert "pass_rates" in data

    def test_variants_present(self, tmp_path, ablate_cup_threshold):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "cup_threshold.json"
        ablate_cup_threshold.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert set(data["variants"]) == {"strict", "tolerant_1", "tolerant_2"}

    def test_pass_rates_in_range(self, tmp_path, ablate_cup_threshold):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "cup_threshold.json"
        ablate_cup_threshold.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        for variant, model_rates in data["pass_rates"].items():
            for model, rate in model_rates.items():
                assert 0.0 <= rate <= 1.0, (
                    f"Pass rate out of [0, 1] for variant={variant}, model={model}: {rate}"
                )

    def test_stricter_threshold_lower_or_equal_pass_rate(self, tmp_path, ablate_cup_threshold):
        """Stricter threshold must yield <= pass rate compared to more tolerant ones."""
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "cup_threshold.json"
        ablate_cup_threshold.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        for model in data["models"]:
            strict = data["pass_rates"]["strict"][model]
            tol1 = data["pass_rates"]["tolerant_1"][model]
            tol2 = data["pass_rates"]["tolerant_2"][model]
            assert strict <= tol1, f"strict > tolerant_1 for {model}: {strict} > {tol1}"
            assert tol1 <= tol2, f"tolerant_1 > tolerant_2 for {model}: {tol1} > {tol2}"

    def test_hard_fail_excluded_from_pass(self, tmp_path, ablate_cup_threshold):
        """Tasks with hard_fail=True should never count as passing, regardless of score."""
        # TASK_003 has aggregate_score=0.30, hard_fail=True
        # TASK_007 has aggregate_score=0.10, hard_fail=True
        # Neither should pass even under tolerant_2 (threshold=0.50) since their scores
        # are too low; but let's verify via a custom dataset with a high-score hard_fail task.
        custom_dir = tmp_path / "custom_v02_dev" / "model_x"
        records = [
            {
                "result_id": "r1", "run_id": "run1", "task_id": "T1",
                "role": "user", "environment_id": "e1", "adapter_name": "a",
                "model_name": "model_x",
                "hard_fail": True,         # high score but hard_fail!
                "aggregate_score": 0.95,
                "dimension_scores": {},
                "timestamp": _TS,
            },
            {
                "result_id": "r2", "run_id": "run1", "task_id": "T2",
                "role": "user", "environment_id": "e1", "adapter_name": "a",
                "model_name": "model_x",
                "hard_fail": False,
                "aggregate_score": 0.80,
                "dimension_scores": {},
                "timestamp": _TS,
            },
        ]
        _write_model_results(custom_dir, records)
        out = tmp_path / "cup_hf.json"
        ablate_cup_threshold.main([
            "--runs", str(tmp_path / "custom_v02_dev"),
            "--output", str(out),
        ])
        data = json.loads(out.read_text(encoding="utf-8"))
        # T1 has hard_fail=True so should NOT count as pass; only T2 passes
        # strict threshold=0.70: T2 (0.80) passes → 1/2 = 0.5
        assert data["pass_rates"]["strict"]["model_x"] == pytest.approx(0.5)

    def test_empty_runs_dir_no_crash(self, tmp_path, ablate_cup_threshold):
        out = tmp_path / "cup_empty.json"
        ret = ablate_cup_threshold.main([
            "--runs", str(tmp_path / "nonexistent"),
            "--output", str(out),
        ])
        assert ret == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["models"] == []
        assert all(v == {} for v in data["pass_rates"].values())


# ---------------------------------------------------------------------------
# E5: difficulty tests
# ---------------------------------------------------------------------------


class TestAblateDifficulty:
    def test_output_file_created(self, tmp_path, ablate_difficulty):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "difficulty.json"
        ret = ablate_difficulty.main(["--runs", str(runs_dir), "--output", str(out)])
        assert ret == 0
        assert out.exists()

    def test_output_valid_json(self, tmp_path, ablate_difficulty):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "difficulty.json"
        ablate_difficulty.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_schema_keys(self, tmp_path, ablate_difficulty):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "difficulty.json"
        ablate_difficulty.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "generated_at" in data
        assert "difficulties" in data
        assert "models" in data
        assert "mean_scores" in data
        assert "ci_95" in data

    def test_difficulties_correct(self, tmp_path, ablate_difficulty):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "difficulty.json"
        ablate_difficulty.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["difficulties"] == ["easy", "medium", "hard"]

    def test_mean_scores_in_range(self, tmp_path, ablate_difficulty):
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "difficulty.json"
        ablate_difficulty.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        for diff, model_scores in data["mean_scores"].items():
            for model, score in model_scores.items():
                if score is not None:
                    assert 0.0 <= score <= 1.0, (
                        f"Mean score out of range for diff={diff}, model={model}: {score}"
                    )

    def test_ci_lower_le_mean_le_upper(self, tmp_path, ablate_difficulty):
        """Bootstrap CI must satisfy lower <= mean <= upper for non-null strata."""
        runs_dir = _write_synthetic_runs(tmp_path)
        out = tmp_path / "difficulty.json"
        ablate_difficulty.main(["--runs", str(runs_dir), "--output", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        for diff in data["difficulties"]:
            for model in data["models"]:
                mean = data["mean_scores"][diff].get(model)
                ci = data["ci_95"][diff].get(model)
                if mean is None:
                    assert ci == [None, None], (
                        f"Expected null CI for null mean: diff={diff}, model={model}"
                    )
                else:
                    lo, hi = ci
                    assert lo is not None and hi is not None
                    assert lo <= mean + 1e-6, (
                        f"CI lower > mean for diff={diff}, model={model}: {lo} > {mean}"
                    )
                    assert mean <= hi + 1e-6, (
                        f"Mean > CI upper for diff={diff}, model={model}: {mean} > {hi}"
                    )

    def test_null_for_missing_stratum(self, tmp_path, ablate_difficulty):
        """A model with no hard tasks should have null mean and ci for hard stratum."""
        custom_dir = tmp_path / "diff_v02_dev" / "model_easy_only"
        records = [
            {
                "result_id": f"r{i}", "run_id": "run1", "task_id": f"T{i:03d}",
                "role": "user", "environment_id": "e1", "adapter_name": "a",
                "model_name": "model_easy_only",
                "hard_fail": False,
                "aggregate_score": 0.8,
                "difficulty": "easy",
                "dimension_scores": {},
                "timestamp": _TS,
            }
            for i in range(5)
        ]
        _write_model_results(custom_dir, records)
        out = tmp_path / "diff_easy_only.json"
        ablate_difficulty.main([
            "--runs", str(tmp_path / "diff_v02_dev"),
            "--output", str(out),
        ])
        data = json.loads(out.read_text(encoding="utf-8"))
        # hard stratum should be null
        assert data["mean_scores"]["hard"]["model_easy_only"] is None
        assert data["ci_95"]["hard"]["model_easy_only"] == [None, None]
        # easy stratum should be non-null
        assert data["mean_scores"]["easy"]["model_easy_only"] is not None

    def test_tier_fallback_used_when_no_difficulty_string(self, tmp_path, ablate_difficulty):
        """task_difficulty_tier should be used when 'difficulty' key is absent."""
        custom_dir = tmp_path / "tier_v02_dev" / "model_tier"
        records = [
            {
                "result_id": "r1", "run_id": "run1", "task_id": "T001",
                "role": "user", "environment_id": "e1", "adapter_name": "a",
                "model_name": "model_tier",
                "hard_fail": False,
                "aggregate_score": 0.7,
                "task_difficulty_tier": 3,  # hard, no 'difficulty' key
                "dimension_scores": {},
                "timestamp": _TS,
            },
        ]
        _write_model_results(custom_dir, records)
        out = tmp_path / "diff_tier.json"
        ablate_difficulty.main([
            "--runs", str(tmp_path / "tier_v02_dev"),
            "--output", str(out),
        ])
        data = json.loads(out.read_text(encoding="utf-8"))
        # Should appear in "hard" stratum
        assert data["mean_scores"]["hard"]["model_tier"] == pytest.approx(0.7, abs=1e-4)

    def test_empty_runs_dir_no_crash(self, tmp_path, ablate_difficulty):
        out = tmp_path / "diff_empty.json"
        ret = ablate_difficulty.main([
            "--runs", str(tmp_path / "nonexistent"),
            "--output", str(out),
        ])
        assert ret == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["models"] == []
        assert all(v == {} for v in data["mean_scores"].values())
        assert all(v == {} for v in data["ci_95"].values())

    def test_malformed_result_file_skipped(self, tmp_path, ablate_difficulty):
        """A malformed result JSON file should be skipped, not crash the run."""
        custom_dir = tmp_path / "malformed_v02_dev" / "model_m"
        valid = [
            {
                "result_id": "r1", "run_id": "run1", "task_id": "T1", "role": "u",
                "environment_id": "e1", "adapter_name": "a", "model_name": "model_m",
                "hard_fail": False, "aggregate_score": 0.5, "difficulty": "easy",
                "dimension_scores": {}, "timestamp": _TS,
            },
            {
                "result_id": "r2", "run_id": "run1", "task_id": "T2", "role": "u",
                "environment_id": "e1", "adapter_name": "a", "model_name": "model_m",
                "hard_fail": False, "aggregate_score": 0.8, "difficulty": "easy",
                "dimension_scores": {}, "timestamp": _TS,
            },
        ]
        _write_model_results(custom_dir, valid)
        # Drop a malformed .json file alongside the valid ones — must be skipped.
        (custom_dir / "run_synth" / "results" / "T3_result.json").write_text(
            "this is not json", encoding="utf-8"
        )
        out = tmp_path / "diff_malformed.json"
        ret = ablate_difficulty.main([
            "--runs", str(tmp_path / "malformed_v02_dev"),
            "--output", str(out),
        ])
        assert ret == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        # Should have processed the 2 valid records (mean of 0.5 and 0.8)
        assert data["mean_scores"]["easy"]["model_m"] == pytest.approx(0.65, abs=1e-4)
