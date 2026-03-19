"""Integration tests: exabench clear run CLI command."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from exabench.cli.main import app
from exabench.schemas.result import BenchmarkResult, DimensionScores

runner = CliRunner()


def _write_result(
    results_dir: Path,
    task_id: str,
    model_name: str,
    aggregate_score: float = 0.8,
    outcome: float = 0.75,
    governance: float = 0.85,
    cost_usd: float = 0.01,
    latency_s: float = 5.0,
) -> None:
    """Write a BenchmarkResult JSON to results_dir."""
    result = BenchmarkResult(
        result_id=f"r_{task_id}",
        run_id="run_test",
        task_id=task_id,
        role="sysadmin",
        environment_id="env_01",
        adapter_name="openai",
        model_name=model_name,
        dimension_scores=DimensionScores(outcome=outcome, governance=governance),
        aggregate_score=aggregate_score,
        cost_estimate_usd=cost_usd,
        latency_seconds=latency_s,
        timestamp=datetime.now(tz=timezone.utc),
    )
    out = results_dir / f"{task_id}_result.json"
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def _make_run_dir(
    tmp_path: Path,
    model_name: str,
    n_tasks: int = 5,
    dir_name: str = "run_test",
) -> Path:
    """Create a run directory with pre-built result JSON files."""
    run_dir = tmp_path / dir_name
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True)

    for i in range(n_tasks):
        _write_result(
            results_dir,
            task_id=f"TASK_{i:03d}",
            model_name=model_name,
        )
    return run_dir


# ── single model ──────────────────────────────────────────────────────────────


def test_clear_cmd_single_model(tmp_path):
    """exabench clear run produces a valid CLEAR report for one run directory."""
    run_dir = _make_run_dir(tmp_path, model_name="gpt-4o", n_tasks=5)
    output_path = tmp_path / "clear_report.json"

    result = runner.invoke(
        app,
        ["clear", "run", "--run-dir", str(run_dir), "--output", str(output_path)],
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()

    report = json.loads(output_path.read_text())
    assert "models" in report
    assert "leaderboard" in report
    assert report["task_count"] == 5

    model_data = report["models"]["gpt-4o"]
    assert model_data["clear_score"] is not None
    assert 0.0 <= model_data["clear_score"] <= 1.0


def test_clear_cmd_output_contains_all_keys(tmp_path):
    """CLEAR report contains all required keys per model."""
    run_dir = _make_run_dir(tmp_path, model_name="test-model", n_tasks=3)
    output_path = tmp_path / "out.json"

    result = runner.invoke(
        app,
        ["clear", "run", "--run-dir", str(run_dir), "--output", str(output_path)],
    )
    assert result.exit_code == 0, result.output

    report = json.loads(output_path.read_text())
    required_keys = {
        "clear_score", "C_norm", "L_norm", "E", "A", "R",
        "mean_cost_usd", "mean_latency_s", "CNA", "CPS",
        "n_tasks", "n_successful",
    }
    for model_name, model_data in report["models"].items():
        missing = required_keys - model_data.keys()
        assert not missing, f"Model {model_name!r} missing keys: {missing}"


# ── multi-model ───────────────────────────────────────────────────────────────


def test_clear_cmd_two_models(tmp_path):
    """Two run dirs with different models → leaderboard has 2 entries sorted desc."""
    run_a = _make_run_dir(tmp_path, model_name="model-fast", n_tasks=4, dir_name="run_a")

    # run_b: higher accuracy but higher cost/latency
    run_b = _make_run_dir(tmp_path, model_name="model-slow", n_tasks=4, dir_name="run_b")
    for f in (run_b / "results").glob("*_result.json"):
        r = BenchmarkResult.model_validate(json.loads(f.read_text()))
        r2 = r.model_copy(
            update={
                "model_name": "model-slow",
                "aggregate_score": 0.9,
                "cost_estimate_usd": 0.05,
                "latency_seconds": 20.0,
            }
        )
        f.write_text(r2.model_dump_json(indent=2), encoding="utf-8")

    output_path = tmp_path / "clear_report.json"
    result = runner.invoke(
        app,
        [
            "clear", "run",
            "--run-dir", str(run_a),
            "--run-dir", str(run_b),
            "--output", str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(output_path.read_text())

    assert len(report["models"]) == 2
    assert len(report["leaderboard"]) == 2

    # Leaderboard must be sorted descending by clear_score
    lb_scores = [e["clear_score"] for e in report["leaderboard"] if e["clear_score"] is not None]
    assert lb_scores == sorted(lb_scores, reverse=True)

    # Ranks must be 1, 2
    ranks = [e["rank"] for e in report["leaderboard"]]
    assert ranks == [1, 2]

    # All clear_scores must be in [0, 1]
    for entry in report["leaderboard"]:
        if entry["clear_score"] is not None:
            assert 0.0 <= entry["clear_score"] <= 1.0


# ── pass_threshold option ─────────────────────────────────────────────────────


def test_clear_cmd_pass_threshold(tmp_path):
    """--pass-threshold affects n_successful and CPS."""
    run_dir = _make_run_dir(tmp_path, model_name="model-x", n_tasks=4)
    # All results have aggregate_score=0.8 → at threshold=0.9 none pass
    for f in (run_dir / "results").glob("*_result.json"):
        r = BenchmarkResult.model_validate(json.loads(f.read_text()))
        r2 = r.model_copy(update={"aggregate_score": 0.8})
        f.write_text(r2.model_dump_json(indent=2), encoding="utf-8")

    output_path = tmp_path / "out.json"
    result = runner.invoke(
        app,
        [
            "clear", "run",
            "--run-dir", str(run_dir),
            "--output", str(output_path),
            "--pass-threshold", "0.9",
        ],
    )
    assert result.exit_code == 0, result.output

    report = json.loads(output_path.read_text())
    assert report["models"]["model-x"]["n_successful"] == 0
    assert report["models"]["model-x"]["CPS"] is None


# ── missing results dir ───────────────────────────────────────────────────────


def test_clear_cmd_no_results_dir(tmp_path):
    """Empty directory produces a non-zero exit code."""
    empty_dir = tmp_path / "empty_run"
    empty_dir.mkdir()
    output_path = tmp_path / "out.json"

    result = runner.invoke(
        app,
        ["clear", "run", "--run-dir", str(empty_dir), "--output", str(output_path)],
    )
    assert result.exit_code != 0
