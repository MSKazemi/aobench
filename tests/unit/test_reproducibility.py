"""Unit tests for aobench.reproducibility (manifest + compute)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aobench.reproducibility.compute import ComputeRecord, append_compute
from aobench.reproducibility.manifest import ManifestRecord, write_manifest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_manifest(**overrides) -> ManifestRecord:
    defaults = dict(
        run_id="run_test_001",
        dataset_version="v0.2.0",
        engine_version="0.2.0",
        agent_model="gpt-4o-2024-11-20",
        split="dev",
        task_ids=["JOB_USR_001", "JOB_USR_002"],
        python_version="3.11.9",
        os_name="Linux-6.1.0-x86_64",
        created_at="2026-05-01T12:00:00Z",
    )
    defaults.update(overrides)
    return ManifestRecord(**defaults)


def _minimal_compute(**overrides) -> ComputeRecord:
    defaults = dict(
        run_id="run_test_001",
        task_id="JOB_USR_001",
        model="gpt-4o-2024-11-20",
    )
    defaults.update(overrides)
    return ComputeRecord(**defaults)


# ── ManifestRecord validation ─────────────────────────────────────────────────

class TestManifestRecord:
    def test_valid_minimal(self):
        record = _minimal_manifest()
        assert record.run_id == "run_test_001"
        assert record.dataset_version == "v0.2.0"
        assert record.engine_version == "0.2.0"
        assert record.agent_model == "gpt-4o-2024-11-20"
        assert record.split == "dev"
        assert record.task_ids == ["JOB_USR_001", "JOB_USR_002"]

    def test_optional_fields_default_none(self):
        record = _minimal_manifest()
        assert record.judge_config_id is None
        assert record.snapshot_bundle_sha256 is None
        assert record.agent_seed is None
        assert record.gpu_info is None

    def test_validity_gates_defaults_empty(self):
        record = _minimal_manifest()
        assert record.validity_gates == {}

    def test_with_optional_fields(self):
        record = _minimal_manifest(
            judge_config_id="abcd1234abcd1234",
            agent_seed=42,
            gpu_info="NVIDIA A100 80GB",
            validity_gates={"V1": True, "V2": False},
        )
        assert record.judge_config_id == "abcd1234abcd1234"
        assert record.agent_seed == 42
        assert record.gpu_info == "NVIDIA A100 80GB"
        assert record.validity_gates == {"V1": True, "V2": False}

    def test_model_dump_is_json_serialisable(self):
        record = _minimal_manifest()
        data = record.model_dump()
        json_str = json.dumps(data)
        assert "run_test_001" in json_str

    def test_task_ids_preserves_order(self):
        ids = ["TASK_C", "TASK_A", "TASK_B"]
        record = _minimal_manifest(task_ids=ids)
        assert record.task_ids == ids


# ── write_manifest ─────────────────────────────────────────────────────────────

class TestWriteManifest:
    def test_writes_file(self, tmp_path):
        record = _minimal_manifest()
        written = write_manifest(record, tmp_path)
        assert written.exists()
        assert written.name == "MANIFEST.json"

    def test_creates_output_dir(self, tmp_path):
        output_dir = tmp_path / "nested" / "run_dir"
        assert not output_dir.exists()
        record = _minimal_manifest()
        write_manifest(record, output_dir)
        assert output_dir.exists()

    def test_content_is_valid_json(self, tmp_path):
        record = _minimal_manifest()
        written = write_manifest(record, tmp_path)
        data = json.loads(written.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_content_matches_record(self, tmp_path):
        record = _minimal_manifest(
            run_id="run_abc",
            agent_model="claude-sonnet-4-6",
            split="public_test",
        )
        written = write_manifest(record, tmp_path)
        data = json.loads(written.read_text(encoding="utf-8"))
        assert data["run_id"] == "run_abc"
        assert data["agent_model"] == "claude-sonnet-4-6"
        assert data["split"] == "public_test"

    def test_overwrites_existing(self, tmp_path):
        record_a = _minimal_manifest(run_id="run_a")
        record_b = _minimal_manifest(run_id="run_b")
        write_manifest(record_a, tmp_path)
        write_manifest(record_b, tmp_path)
        data = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
        assert data["run_id"] == "run_b"

    def test_returns_path_to_manifest(self, tmp_path):
        record = _minimal_manifest()
        result = write_manifest(record, tmp_path)
        assert isinstance(result, Path)
        assert result == tmp_path / "MANIFEST.json"


# ── ComputeRecord validation ──────────────────────────────────────────────────

class TestComputeRecord:
    def test_valid_minimal(self):
        record = _minimal_compute()
        assert record.run_id == "run_test_001"
        assert record.task_id == "JOB_USR_001"
        assert record.model == "gpt-4o-2024-11-20"

    def test_optional_fields_default_none(self):
        record = _minimal_compute()
        assert record.prompt_tokens is None
        assert record.completion_tokens is None
        assert record.cost_usd is None
        assert record.wall_clock_seconds is None
        assert record.gpu_energy_wh is None
        assert record.co2_g is None

    def test_open_weight_defaults_false(self):
        record = _minimal_compute()
        assert record.open_weight is False

    def test_with_full_fields(self):
        record = _minimal_compute(
            prompt_tokens=1500,
            completion_tokens=300,
            cost_usd=0.015,
            wall_clock_seconds=12.4,
            open_weight=True,
            gpu_energy_wh=0.05,
            co2_g=0.022,
        )
        assert record.prompt_tokens == 1500
        assert record.completion_tokens == 300
        assert record.cost_usd == 0.015
        assert record.open_weight is True
        assert record.gpu_energy_wh == 0.05
        assert record.co2_g == 0.022

    def test_model_dump_is_json_serialisable(self):
        record = _minimal_compute()
        data = record.model_dump()
        json_str = json.dumps(data)
        assert "run_test_001" in json_str


# ── append_compute ────────────────────────────────────────────────────────────

class TestAppendCompute:
    def test_creates_file(self, tmp_path):
        record = _minimal_compute()
        append_compute(record, tmp_path)
        assert (tmp_path / "COMPUTE.jsonl").exists()

    def test_creates_output_dir(self, tmp_path):
        output_dir = tmp_path / "nested" / "run_dir"
        assert not output_dir.exists()
        record = _minimal_compute()
        append_compute(record, output_dir)
        assert output_dir.exists()

    def test_single_record_is_valid_json_line(self, tmp_path):
        record = _minimal_compute(task_id="TASK_001")
        append_compute(record, tmp_path)
        lines = (tmp_path / "COMPUTE.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["task_id"] == "TASK_001"

    def test_appends_multiple_records(self, tmp_path):
        for i in range(3):
            record = _minimal_compute(task_id=f"TASK_{i:03d}")
            append_compute(record, tmp_path)
        lines = (tmp_path / "COMPUTE.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        task_ids = [json.loads(line)["task_id"] for line in lines]
        assert task_ids == ["TASK_000", "TASK_001", "TASK_002"]

    def test_records_have_newline_separator(self, tmp_path):
        for _ in range(2):
            append_compute(_minimal_compute(), tmp_path)
        raw = (tmp_path / "COMPUTE.jsonl").read_text(encoding="utf-8")
        assert raw.endswith("\n")
        # Each line ends with \n — check we have exactly 2 non-empty lines
        assert len([l for l in raw.splitlines() if l.strip()]) == 2

    def test_record_fields_persisted(self, tmp_path):
        record = _minimal_compute(
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=0.005,
            open_weight=False,
        )
        append_compute(record, tmp_path)
        data = json.loads(
            (tmp_path / "COMPUTE.jsonl").read_text(encoding="utf-8").strip()
        )
        assert data["prompt_tokens"] == 100
        assert data["completion_tokens"] == 50
        assert data["cost_usd"] == 0.005
        assert data["open_weight"] is False
