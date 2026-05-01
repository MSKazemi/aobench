"""Tests for task authoring tooling: oracle_check and independence_check."""

from __future__ import annotations

import json
import math
import pathlib
import sys
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Helpers to import the scripts as modules
# ---------------------------------------------------------------------------

def _import_oracle_check():
    """Import oracle_check from scripts/ directory."""
    scripts_dir = pathlib.Path(__file__).parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    import oracle_check
    return oracle_check


def _import_independence_check():
    """Import independence_check from scripts/ directory."""
    scripts_dir = pathlib.Path(__file__).parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    import independence_check
    return independence_check


# ---------------------------------------------------------------------------
# oracle_check tests
# ---------------------------------------------------------------------------


class TestOracleCheck:
    def setup_method(self):
        self.oracle = _import_oracle_check()

    def _write_task(self, tmp_path: pathlib.Path, data: dict) -> pathlib.Path:
        task_file = tmp_path / f"{data['task_id']}.json"
        task_file.write_text(json.dumps(data))
        return task_file

    def test_missing_env_dir_fails(self, tmp_path: pathlib.Path):
        """Task should FAIL when its environment directory does not exist."""
        task_data = {
            "task_id": "TEST_001",
            "environment_id": "env_nonexistent",
            "gold_evidence_refs": [],
            "eval_criteria": {"gold_answer": "Some answer"},
        }
        task_file = self._write_task(tmp_path, task_data)
        env_dir = str(tmp_path / "environments")

        task_id, passed, reason = self.oracle.check_task(task_file, env_dir)
        assert task_id == "TEST_001"
        assert not passed
        assert "env dir missing" in reason

    def test_missing_gold_answer_fails(self, tmp_path: pathlib.Path):
        """Task should FAIL when gold_answer is absent or empty."""
        # Create env dir so that check passes the env check
        env_dir = tmp_path / "environments"
        (env_dir / "env_test").mkdir(parents=True)

        task_data = {
            "task_id": "TEST_002",
            "environment_id": "env_test",
            "gold_evidence_refs": [],
            "eval_criteria": {"gold_answer": None},
        }
        task_file = self._write_task(tmp_path, task_data)

        task_id, passed, reason = self.oracle.check_task(task_file, str(env_dir))
        assert task_id == "TEST_002"
        assert not passed
        assert "gold_answer missing" in reason

    def test_missing_gold_answer_empty_string_fails(self, tmp_path: pathlib.Path):
        """Task should FAIL when gold_answer is empty string."""
        env_dir = tmp_path / "environments"
        (env_dir / "env_test").mkdir(parents=True)

        task_data = {
            "task_id": "TEST_003",
            "environment_id": "env_test",
            "gold_evidence_refs": [],
            "eval_criteria": {"gold_answer": ""},
        }
        task_file = self._write_task(tmp_path, task_data)

        task_id, passed, reason = self.oracle.check_task(task_file, str(env_dir))
        assert not passed
        assert "gold_answer missing" in reason

    def test_missing_eval_criteria_fails(self, tmp_path: pathlib.Path):
        """Task should FAIL when eval_criteria is absent entirely."""
        env_dir = tmp_path / "environments"
        (env_dir / "env_test").mkdir(parents=True)

        task_data = {
            "task_id": "TEST_004",
            "environment_id": "env_test",
            "gold_evidence_refs": [],
        }
        task_file = self._write_task(tmp_path, task_data)

        task_id, passed, reason = self.oracle.check_task(task_file, str(env_dir))
        assert not passed
        assert "gold_answer missing" in reason

    def test_missing_evidence_file_fails(self, tmp_path: pathlib.Path):
        """Task should FAIL when a gold_evidence_ref file is missing from the env."""
        env_dir = tmp_path / "environments"
        (env_dir / "env_test").mkdir(parents=True)
        # Do NOT create slurm/job_details.json

        task_data = {
            "task_id": "TEST_005",
            "environment_id": "env_test",
            "gold_evidence_refs": ["slurm/job_details.json#oom_evidence"],
            "eval_criteria": {"gold_answer": "The answer is 42."},
        }
        task_file = self._write_task(tmp_path, task_data)

        task_id, passed, reason = self.oracle.check_task(task_file, str(env_dir))
        assert not passed
        assert "evidence missing" in reason

    def test_valid_task_passes(self, tmp_path: pathlib.Path):
        """Task with existing env dir, gold_answer, and all evidence files should PASS."""
        env_dir = tmp_path / "environments"
        env_test = env_dir / "env_test"
        (env_test / "slurm").mkdir(parents=True)
        (env_test / "slurm" / "job_details.json").write_text("{}")

        task_data = {
            "task_id": "TEST_006",
            "environment_id": "env_test",
            "gold_evidence_refs": ["slurm/job_details.json#oom_evidence"],
            "eval_criteria": {"gold_answer": "Job failed due to OOM."},
        }
        task_file = self._write_task(tmp_path, task_data)

        task_id, passed, reason = self.oracle.check_task(task_file, str(env_dir))
        assert task_id == "TEST_006"
        assert passed
        assert reason == "ok"

    def test_valid_task_no_refs_passes(self, tmp_path: pathlib.Path):
        """Task with empty gold_evidence_refs and valid gold_answer should PASS."""
        env_dir = tmp_path / "environments"
        (env_dir / "env_test").mkdir(parents=True)

        task_data = {
            "task_id": "TEST_007",
            "environment_id": "env_test",
            "gold_evidence_refs": [],
            "eval_criteria": {"gold_answer": "The answer is documented in policy."},
        }
        task_file = self._write_task(tmp_path, task_data)

        task_id, passed, reason = self.oracle.check_task(task_file, str(env_dir))
        assert passed
        assert reason == "ok"

    def test_existing_fixture_passes(self):
        """Existing test_task_001.json with test_env_01 should load but may fail oracle
        (env dir may or may not have all files). We just verify check_task runs without error."""
        repo_root = pathlib.Path(__file__).parent.parent.parent
        task_file = repo_root / "tests" / "data" / "tasks" / "test_task_001.json"
        env_dir = repo_root / "tests" / "data" / "environments"

        # Just verify the function runs and returns the expected 3-tuple
        result = self.oracle.check_task(task_file, str(env_dir))
        assert len(result) == 3
        task_id, passed, reason = result
        assert isinstance(task_id, str)
        assert isinstance(passed, bool)
        assert isinstance(reason, str)

    def test_main_returns_int(self, tmp_path: pathlib.Path):
        """main() should return 0 when task dir is empty (no tasks to check)."""
        empty_dir = tmp_path / "specs"
        empty_dir.mkdir()
        rc = self.oracle.main(["--task-dir", str(empty_dir), "--env-dir", str(tmp_path)])
        assert rc == 0


# ---------------------------------------------------------------------------
# independence_check tests
# ---------------------------------------------------------------------------


class TestIndependenceCheck:
    def setup_method(self):
        self.ic = _import_independence_check()

    def test_vector_different_tasks_low_similarity(self):
        """Two clearly different tasks should have cosine similarity < 0.95."""
        task_a = {
            "difficulty": "easy",
            "gold_evidence_refs": [],
            "query_text": "What is the job state?",
            "eval_criteria": {"gold_answer": "Running."},
            "allowed_tools": ["slurm"],
        }
        task_b = {
            "difficulty": "hard",
            "gold_evidence_refs": [f"ref_{i}.json" for i in range(8)],
            "query_text": "x" * 400,
            "eval_criteria": {"gold_answer": "y" * 900},
            "allowed_tools": ["docs", "facility"],
        }
        vec_a = self.ic._build_vector(task_a)
        vec_b = self.ic._build_vector(task_b)
        sim = self.ic._cosine_similarity(vec_a, vec_b)
        assert sim < 0.95, f"Expected sim < 0.95, got {sim}"

    def test_identical_task_has_max_similarity(self):
        """A task compared to itself should have cosine similarity of 1.0."""
        task = {
            "difficulty": "medium",
            "gold_evidence_refs": ["slurm/job.json"],
            "query_text": "What happened to job 12345?",
            "eval_criteria": {"gold_answer": "Job failed."},
            "allowed_tools": ["slurm"],
        }
        vec = self.ic._build_vector(task)
        sim = self.ic._cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 1e-9

    def test_zero_vector_similarity(self):
        """Zero vectors should return similarity of 0.0 (not crash)."""
        vec_a = [0.0, 0.0, 0.0, 0.0, 0.0]
        vec_b = [1.0, 0.0, 0.0, 0.0, 0.0]
        sim = self.ic._cosine_similarity(vec_a, vec_b)
        assert sim == 0.0

    def test_build_vector_clips_to_unit_interval(self):
        """Vector components should all be in [0, 1]."""
        task = {
            "difficulty": "hard",
            "gold_evidence_refs": [f"f{i}.json" for i in range(50)],  # >> 10
            "query_text": "x" * 2000,  # >> 500
            "eval_criteria": {"gold_answer": "y" * 5000},  # >> 1000
            "allowed_tools": ["slurm"],
        }
        vec = self.ic._build_vector(task)
        for component in vec:
            assert 0.0 <= component <= 1.0

    def test_main_no_flagged_returns_0(self, tmp_path: pathlib.Path):
        """main() should return 0 when no near-duplicate pairs found."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        # Write two clearly different tasks
        (specs_dir / "TASK_A.json").write_text(json.dumps({
            "task_id": "TASK_A",
            "difficulty": "easy",
            "gold_evidence_refs": [],
            "query_text": "Simple job lookup",
            "eval_criteria": {"gold_answer": "Running"},
            "allowed_tools": ["slurm"],
        }))
        (specs_dir / "TASK_B.json").write_text(json.dumps({
            "task_id": "TASK_B",
            "difficulty": "hard",
            "gold_evidence_refs": ["a.json", "b.json", "c.json", "d.json", "e.json"],
            "query_text": "x" * 400,
            "eval_criteria": {"gold_answer": "y" * 900},
            "allowed_tools": ["docs"],
        }))

        rc = self.ic.main(["--task-dir", str(specs_dir)])
        assert rc == 0

    def test_main_flags_duplicates_returns_1(self, tmp_path: pathlib.Path):
        """main() should return 1 when near-duplicate pairs are found."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        same_task_data = {
            "difficulty": "medium",
            "gold_evidence_refs": ["slurm/job.json"],
            "query_text": "What happened to job 12345?",
            "eval_criteria": {"gold_answer": "Job failed."},
            "allowed_tools": ["slurm"],
        }

        (specs_dir / "TASK_X.json").write_text(json.dumps({**same_task_data, "task_id": "TASK_X"}))
        (specs_dir / "TASK_Y.json").write_text(json.dumps({**same_task_data, "task_id": "TASK_Y"}))

        rc = self.ic.main(["--task-dir", str(specs_dir), "--threshold", "0.95"])
        assert rc == 1
