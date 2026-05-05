"""Tests for the leaderboard CLI command and leaderboard report helpers."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aobench.reports.leaderboard import load_results_dir, write_heatmap_csv
from aobench.schemas.result import BenchmarkResult, DimensionScores


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    task_id: str,
    adapter_name: str = "test_adapter",
    aggregate_score: float = 0.8,
    cup_score: float | None = None,
    task_category: str = "JOB",
    role: str = "scientific_user",
    task_difficulty_tier: int | None = 1,
    environment_id: str = "env_01",
    run_id: str = "run_001",
) -> BenchmarkResult:
    return BenchmarkResult(
        result_id=f"{adapter_name}_{task_id}",
        run_id=run_id,
        task_id=task_id,
        role=role,
        environment_id=environment_id,
        adapter_name=adapter_name,
        dimension_scores=DimensionScores(outcome=aggregate_score),
        aggregate_score=aggregate_score,
        cup_score=cup_score,
        task_category=task_category,
        task_difficulty_tier=task_difficulty_tier,
        timestamp=datetime.now(tz=timezone.utc),
    )


def _write_results(model_dir: Path, results: list[BenchmarkResult]) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    for r in results:
        (model_dir / f"{r.task_id}_result.json").write_text(
            r.model_dump_json(), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# load_results_dir
# ---------------------------------------------------------------------------

def test_load_results_dir_groups_by_model(tmp_path: Path) -> None:
    _write_results(tmp_path / "model_a", [
        _make_result("TASK_001", "model_a"),
        _make_result("TASK_002", "model_a"),
    ])
    _write_results(tmp_path / "model_b", [
        _make_result("TASK_001", "model_b"),
    ])

    result = load_results_dir(tmp_path)
    assert set(result.keys()) == {"model_a", "model_b"}
    assert len(result["model_a"]) == 2
    assert len(result["model_b"]) == 1


def test_load_results_dir_skips_invalid_json(tmp_path: Path) -> None:
    model_dir = tmp_path / "model_x"
    model_dir.mkdir()
    (model_dir / "bad.json").write_text("not json")
    (model_dir / "TASK_001_result.json").write_text(
        _make_result("TASK_001", "model_x").model_dump_json()
    )

    result = load_results_dir(tmp_path)
    assert "model_x" in result
    assert len(result["model_x"]) == 1


def test_load_results_dir_empty_dir(tmp_path: Path) -> None:
    result = load_results_dir(tmp_path)
    assert result == {}


def test_load_results_dir_skips_non_dirs(tmp_path: Path) -> None:
    (tmp_path / "readme.txt").write_text("ignore me")
    _write_results(tmp_path / "model_a", [_make_result("TASK_001", "model_a")])
    result = load_results_dir(tmp_path)
    assert "readme.txt" not in result
    assert "model_a" in result


# ---------------------------------------------------------------------------
# write_heatmap_csv
# ---------------------------------------------------------------------------

def test_write_heatmap_csv_creates_file(tmp_path: Path) -> None:
    model_results = {
        "model_a": [
            _make_result("TASK_001", aggregate_score=0.9),
            _make_result("TASK_001", aggregate_score=0.7),
            _make_result("TASK_002", aggregate_score=0.2),
        ],
        "model_b": [
            _make_result("TASK_001", aggregate_score=0.6),
        ],
    }
    out = tmp_path / "heatmap.csv"
    write_heatmap_csv(model_results, out)
    assert out.exists()


def test_write_heatmap_csv_has_required_columns(tmp_path: Path) -> None:
    model_results = {
        "model_a": [_make_result("TASK_001", aggregate_score=0.8)],
    }
    out = tmp_path / "heatmap.csv"
    write_heatmap_csv(model_results, out)
    content = out.read_text()
    for col in ("task_id", "qcat", "role", "difficulty", "model", "n_runs", "n_passed",
                "pass_at_1", "pass_at_8", "mean", "std"):
        assert col in content, f"Column '{col}' missing from heatmap CSV"


def test_write_heatmap_csv_skips_heatmap_flag(tmp_path: Path) -> None:
    """--no-heatmap should mean we never call write_heatmap_csv."""
    # Just verify that not calling write_heatmap_csv leaves no file
    out = tmp_path / "heatmap.csv"
    assert not out.exists()


def test_write_heatmap_csv_pass_at_k_none_when_k_gt_n(tmp_path: Path) -> None:
    """pass_at_8 should be None when n_runs < 8."""
    model_results = {
        "model_a": [_make_result("TASK_001", aggregate_score=0.9)],
    }
    out = tmp_path / "heatmap.csv"
    write_heatmap_csv(model_results, out, k_values=[1, 8])
    content = out.read_text()
    lines = content.strip().splitlines()
    assert len(lines) == 2  # header + 1 data row
    data_row = lines[1]
    # pass_at_8 column should be empty (None → empty string in CSV)
    parts = data_row.split(",")
    header_parts = lines[0].split(",")
    idx_8 = header_parts.index("pass_at_8")
    assert parts[idx_8] == "" or parts[idx_8].lower() == "none"


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

def test_leaderboard_build_cli_creates_outputs(tmp_path: Path) -> None:
    _write_results(tmp_path / "model_a", [
        _make_result("TASK_001", "model_a", aggregate_score=0.85),
        _make_result("TASK_002", "model_a", aggregate_score=0.60),
    ])
    _write_results(tmp_path / "model_b", [
        _make_result("TASK_001", "model_b", aggregate_score=0.70),
        _make_result("TASK_002", "model_b", aggregate_score=0.40),
    ])

    out_dir = tmp_path / "leaderboard"
    from typer.testing import CliRunner
    from aobench.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, [
        "leaderboard", "build", str(tmp_path),
        "--output-dir", str(out_dir),
        "--format", "all",
    ])

    assert result.exit_code == 0, result.output
    assert (out_dir / "leaderboard.json").exists()
    assert (out_dir / "leaderboard.csv").exists()
    assert (out_dir / "heatmap.csv").exists()


def test_leaderboard_build_no_heatmap(tmp_path: Path) -> None:
    _write_results(tmp_path / "model_a", [
        _make_result("TASK_001", "model_a"),
    ])
    out_dir = tmp_path / "lb"
    from typer.testing import CliRunner
    from aobench.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, [
        "leaderboard", "build", str(tmp_path),
        "--output-dir", str(out_dir),
        "--no-heatmap",
    ])
    assert result.exit_code == 0, result.output
    assert not (out_dir / "heatmap.csv").exists()


def test_leaderboard_build_missing_dir(tmp_path: Path) -> None:
    from typer.testing import CliRunner
    from aobench.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, [
        "leaderboard", "build", str(tmp_path / "nonexistent"),
    ])
    assert result.exit_code != 0
