"""Tests for MANIFEST.json and COMPUTE.json emission per run directory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

BENCHMARK_ROOT = Path(__file__).parent.parent.parent / "benchmark"


# ── write_run_manifest ────────────────────────────────────────────────────────


class TestWriteRunManifest:
    def test_creates_manifest_json(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")

        assert (tmp_path / "MANIFEST.json").exists()

    def test_manifest_is_valid_json(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")

        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_manifest_contains_dataset_version(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        write_run_manifest(tmp_path, model="test_model", adapter="direct_qa", split="all")

        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert "dataset_version" in data
        assert data["dataset_version"] == "aobench-v0.2.0"

    def test_manifest_contains_commit_hash(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        write_run_manifest(tmp_path, model="test_model", adapter="direct_qa", split="dev")

        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert "commit_hash" in data
        # commit_hash is either a real hash or the fallback "unknown"
        assert isinstance(data["commit_hash"], str)
        assert len(data["commit_hash"]) > 0

    def test_manifest_model_adapter_split(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        write_run_manifest(tmp_path, model="gpt-4o", adapter="openai:gpt-4o", split="lite")

        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert data["model"] == "gpt-4o"
        assert data["adapter"] == "openai:gpt-4o"
        assert data["split"] == "lite"

    def test_manifest_has_started_at(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")

        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert "started_at" in data
        assert data["started_at"] is not None

    def test_manifest_finished_at_initially_none(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")

        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert data.get("finished_at") is None

    def test_creates_run_dir_if_absent(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        nested = tmp_path / "runs" / "run_20260101_120000_abc12345"
        assert not nested.exists()

        write_run_manifest(nested, model="direct_qa", adapter="direct_qa", split="dev")

        assert nested.exists()
        assert (nested / "MANIFEST.json").exists()

    def test_explicit_judge_config_id(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest

        write_run_manifest(
            tmp_path,
            model="direct_qa",
            adapter="direct_qa",
            split="dev",
            judge_config_id="deadbeef12345678",
        )

        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert data["judge_config_id"] == "deadbeef12345678"


# ── finalize_run_artifacts ────────────────────────────────────────────────────


class TestFinalizeRunArtifacts:
    def _make_result(self, *, cost_usd=0.01, latency_s=2.5, prompt_tokens=100, completion_tokens=50):
        """Create a minimal mock result with cost/latency fields."""
        from types import SimpleNamespace
        return SimpleNamespace(
            cost_estimate_usd=cost_usd,
            latency_seconds=latency_s,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def test_creates_compute_json(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")
        finalize_run_artifacts(tmp_path, [self._make_result()])

        assert (tmp_path / "COMPUTE.json").exists()

    def test_compute_json_is_valid_json(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")
        finalize_run_artifacts(tmp_path, [self._make_result()])

        data = json.loads((tmp_path / "COMPUTE.json").read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_compute_json_contains_total_tokens_in(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")
        finalize_run_artifacts(tmp_path, [self._make_result(prompt_tokens=200)])

        data = json.loads((tmp_path / "COMPUTE.json").read_text(encoding="utf-8"))
        assert "total_tokens_in" in data
        assert data["total_tokens_in"] == 200

    def test_compute_json_contains_total_usd(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")
        finalize_run_artifacts(tmp_path, [self._make_result(cost_usd=0.05)])

        data = json.loads((tmp_path / "COMPUTE.json").read_text(encoding="utf-8"))
        assert "total_usd" in data
        assert abs(data["total_usd"] - 0.05) < 1e-9

    def test_compute_json_aggregates_multiple_results(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")
        results = [
            self._make_result(cost_usd=0.01, latency_s=1.0, prompt_tokens=100),
            self._make_result(cost_usd=0.02, latency_s=2.0, prompt_tokens=200),
            self._make_result(cost_usd=0.03, latency_s=3.0, prompt_tokens=300),
        ]
        finalize_run_artifacts(tmp_path, results)

        data = json.loads((tmp_path / "COMPUTE.json").read_text(encoding="utf-8"))
        assert abs(data["total_usd"] - 0.06) < 1e-9
        assert data["total_tokens_in"] == 600
        assert data["task_count"] == 3
        assert abs(data["per_task_avg_usd"] - 0.02) < 1e-9

    def test_compute_json_handles_none_results(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")
        # Mix of (task_id, result) tuples including a failed task (None)
        finalize_run_artifacts(tmp_path, [("TASK_001", self._make_result()), ("TASK_002", None)])

        data = json.loads((tmp_path / "COMPUTE.json").read_text(encoding="utf-8"))
        assert data["task_count"] == 2  # failed task still counted
        assert data["total_tokens_in"] > 0  # from the one successful result

    def test_compute_json_handles_missing_fields(self, tmp_path):
        """Results lacking cost/latency fields should default to 0 without crashing."""
        from types import SimpleNamespace
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")
        bare_result = SimpleNamespace()  # no cost/latency attributes at all

        finalize_run_artifacts(tmp_path, [bare_result])

        data = json.loads((tmp_path / "COMPUTE.json").read_text(encoding="utf-8"))
        assert data["total_usd"] == 0.0
        assert data["total_tokens_in"] == 0

    def test_manifest_finished_at_set_after_finalize(self, tmp_path):
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

        write_run_manifest(tmp_path, model="direct_qa", adapter="direct_qa", split="dev")
        finalize_run_artifacts(tmp_path, [self._make_result()])

        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert data.get("finished_at") is not None

    def test_finalize_without_prior_manifest(self, tmp_path):
        """finalize_run_artifacts must not crash even if MANIFEST.json was never written."""
        from aobench.runners.run_artifacts import finalize_run_artifacts

        # No write_run_manifest call — run_dir may not even exist yet
        finalize_run_artifacts(tmp_path, [])

        assert (tmp_path / "COMPUTE.json").exists()


# ── End-to-end: dry run via direct_qa adapter ─────────────────────────────────


class TestDryRunArtifacts:
    def test_dry_run_emits_manifest_and_compute(self, tmp_path):
        """After a full BenchmarkRunner dry run, both artifact files must exist."""
        from aobench.adapters.direct_qa_adapter import DirectQAAdapter
        from aobench.runners.runner import BenchmarkRunner
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts
        from aobench.utils.ids import make_run_id

        run_id = make_run_id()
        run_dir = tmp_path / run_id

        write_run_manifest(
            run_dir,
            model="direct_qa",
            adapter="direct_qa",
            split="dev",
        )

        runner = BenchmarkRunner(
            adapter=DirectQAAdapter(answer="Job 891234 failed due to OOM."),
            benchmark_root=BENCHMARK_ROOT,
            output_root=tmp_path,
        )
        result = runner.run("JOB_USR_001", "env_01", run_id=run_id)

        finalize_run_artifacts(run_dir, [result])

        assert (run_dir / "MANIFEST.json").exists(), "MANIFEST.json missing"
        assert (run_dir / "COMPUTE.json").exists(), "COMPUTE.json missing"

    def test_dry_run_manifest_has_required_keys(self, tmp_path):
        """MANIFEST.json must contain dataset_version and commit_hash."""
        from aobench.adapters.direct_qa_adapter import DirectQAAdapter
        from aobench.runners.runner import BenchmarkRunner
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts
        from aobench.utils.ids import make_run_id

        run_id = make_run_id()
        run_dir = tmp_path / run_id

        write_run_manifest(run_dir, model="direct_qa", adapter="direct_qa", split="dev")

        runner = BenchmarkRunner(
            adapter=DirectQAAdapter(answer="OOM kill."),
            benchmark_root=BENCHMARK_ROOT,
            output_root=tmp_path,
        )
        runner.run("JOB_USR_001", "env_01", run_id=run_id)

        finalize_run_artifacts(run_dir, [])

        data = json.loads((run_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        assert "dataset_version" in data
        assert "commit_hash" in data
        assert data["dataset_version"] == "aobench-v0.2.0"

    def test_dry_run_compute_has_required_keys(self, tmp_path):
        """COMPUTE.json must contain total_tokens_in and total_usd."""
        from aobench.adapters.direct_qa_adapter import DirectQAAdapter
        from aobench.runners.runner import BenchmarkRunner
        from aobench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts
        from aobench.utils.ids import make_run_id

        run_id = make_run_id()
        run_dir = tmp_path / run_id

        write_run_manifest(run_dir, model="direct_qa", adapter="direct_qa", split="dev")

        runner = BenchmarkRunner(
            adapter=DirectQAAdapter(answer="OOM kill."),
            benchmark_root=BENCHMARK_ROOT,
            output_root=tmp_path,
        )
        result = runner.run("JOB_USR_001", "env_01", run_id=run_id)

        finalize_run_artifacts(run_dir, [result])

        data = json.loads((run_dir / "COMPUTE.json").read_text(encoding="utf-8"))
        assert "total_tokens_in" in data
        assert "total_usd" in data
        assert "task_count" in data
        assert data["task_count"] == 1
