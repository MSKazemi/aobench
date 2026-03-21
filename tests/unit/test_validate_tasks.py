"""Unit tests for the task validator framework (T1–T10) and CLI scripts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Base dataclass tests
# ---------------------------------------------------------------------------

class TestCheckResult:
    def test_pass_result(self):
        from exabench.cli.validators.base import CheckResult
        r = CheckResult(status="PASS", detail="All good.")
        assert r.status == "PASS"
        assert r.detail == "All good."
        assert r.fix_suggestion is None

    def test_fail_result_with_suggestion(self):
        from exabench.cli.validators.base import CheckResult
        r = CheckResult(status="FAIL", detail="Bad.", fix_suggestion="Fix it.")
        assert r.status == "FAIL"
        assert r.fix_suggestion == "Fix it."

    def test_warn_result(self):
        from exabench.cli.validators.base import CheckResult
        r = CheckResult(status="WARN", detail="Watch out.")
        assert r.status == "WARN"

    def test_skip_result(self):
        from exabench.cli.validators.base import CheckResult
        r = CheckResult(status="SKIP", detail="Skipped.")
        assert r.status == "SKIP"


class TestTaskValidityResult:
    def test_pass_result_is_release_ready(self):
        from exabench.cli.validators.base import CheckResult, TaskValidityResult
        r = TaskValidityResult(
            task_id="test_01",
            overall="PASS",
            checks={"t1": CheckResult(status="PASS", detail="ok")},
        )
        assert r.release_ready is True

    def test_warn_result_is_not_release_ready(self):
        from exabench.cli.validators.base import CheckResult, TaskValidityResult
        r = TaskValidityResult(
            task_id="test_01",
            overall="WARN",
            checks={"t8": CheckResult(status="WARN", detail="missing comparison_mode")},
        )
        assert r.release_ready is False

    def test_fail_result_is_not_release_ready(self):
        from exabench.cli.validators.base import CheckResult, TaskValidityResult
        r = TaskValidityResult(
            task_id="test_01",
            overall="FAIL",
            checks={"t1": CheckResult(status="FAIL", detail="tool missing from catalog")},
        )
        assert r.release_ready is False


class TestAggregateOverall:
    def test_all_pass(self):
        from exabench.cli.validators.base import CheckResult, aggregate_overall
        checks = {
            "t1": CheckResult(status="PASS", detail="ok"),
            "t2": CheckResult(status="PASS", detail="ok"),
        }
        assert aggregate_overall(checks) == "PASS"

    def test_any_fail(self):
        from exabench.cli.validators.base import CheckResult, aggregate_overall
        checks = {
            "t1": CheckResult(status="PASS", detail="ok"),
            "t3": CheckResult(status="FAIL", detail="bad"),
        }
        assert aggregate_overall(checks) == "FAIL"

    def test_warn_without_strict(self):
        from exabench.cli.validators.base import CheckResult, aggregate_overall
        checks = {
            "t8": CheckResult(status="WARN", detail="minor issue"),
        }
        assert aggregate_overall(checks, strict=False) == "WARN"

    def test_warn_with_strict(self):
        from exabench.cli.validators.base import CheckResult, aggregate_overall
        checks = {
            "t8": CheckResult(status="WARN", detail="minor issue"),
        }
        assert aggregate_overall(checks, strict=True) == "FAIL"

    def test_skip_counts_as_pass(self):
        from exabench.cli.validators.base import CheckResult, aggregate_overall
        checks = {
            "t2": CheckResult(status="SKIP", detail="no snapshot"),
            "t6": CheckResult(status="PASS", detail="ok"),
        }
        assert aggregate_overall(checks) == "PASS"


# ---------------------------------------------------------------------------
# Schema additions
# ---------------------------------------------------------------------------

class TestSchemaAdditions:
    def test_hpc_ground_truth_has_comparison_mode(self):
        from exabench.schemas.task import HPCGroundTruth
        gt = HPCGroundTruth(comparison_mode="exact")
        assert gt.comparison_mode == "exact"

    def test_hpc_ground_truth_has_derivation_query(self):
        from exabench.schemas.task import HPCGroundTruth
        gt = HPCGroundTruth(derivation_query="slurm/jobs.json:job_state")
        assert gt.derivation_query == "slurm/jobs.json:job_state"

    def test_hpc_ground_truth_defaults_are_none(self):
        from exabench.schemas.task import HPCGroundTruth
        gt = HPCGroundTruth()
        assert gt.comparison_mode is None
        assert gt.derivation_query is None

    def test_hpc_task_spec_has_ground_truth_files_excluded(self):
        from exabench.schemas.task import HPCGroundTruth, HPCTaskSpec
        task = HPCTaskSpec(
            task_id="test_01",
            question="What?",
            data_type="job_ops",
            workload_type="OLAP",
            temporal="retrospective",
            scoring_mode="deterministic",
            difficulty="easy",
            snapshot_id="env_01",
            ground_truth_files_excluded=["incidents/inc_001.json"],
        )
        assert task.ground_truth_files_excluded == ["incidents/inc_001.json"]

    def test_hpc_task_spec_has_temporal_anchor(self):
        from exabench.schemas.task import HPCTaskSpec
        task = HPCTaskSpec(
            task_id="test_02",
            question="What happened last week?",
            data_type="job_ops",
            workload_type="OLAP",
            temporal="retrospective",
            scoring_mode="deterministic",
            difficulty="easy",
            snapshot_id="env_01",
            temporal_anchor="snapshot_timestamp",
        )
        assert task.temporal_anchor == "snapshot_timestamp"

    def test_hpc_task_spec_defaults(self):
        from exabench.schemas.task import HPCTaskSpec
        task = HPCTaskSpec(
            task_id="test_03",
            question="Q?",
            data_type="telemetry",
            workload_type="OLTP",
            temporal="retrospective",
            scoring_mode="deterministic",
            difficulty="easy",
            snapshot_id="env_01",
        )
        assert task.ground_truth_files_excluded == []
        assert task.temporal_anchor is None


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_task(**kwargs) -> Any:
    """Create a minimal HPCTaskSpec for testing."""
    from exabench.schemas.task import HPCTaskSpec
    defaults = dict(
        task_id="t_test_01",
        question="What is the state of job 123?",
        data_type="job_ops",
        workload_type="OLAP",
        temporal="retrospective",
        scoring_mode="deterministic",
        difficulty="easy",
        snapshot_id="env_01",
    )
    defaults.update(kwargs)
    return HPCTaskSpec(**defaults)


def _make_catalog_mock(tool_names: list[str], version: str = "1.0") -> MagicMock:
    """Build a mock ToolCatalog."""
    catalog = MagicMock()
    catalog.version = version

    def get_tool(name):
        if name in tool_names:
            return MagicMock(name=name)
        raise KeyError(f"Tool '{name}' not in catalog")

    catalog.get_tool.side_effect = get_tool
    catalog.tools = [MagicMock(name=n) for n in tool_names]
    return catalog


# ---------------------------------------------------------------------------
# T1: tool version pinning
# ---------------------------------------------------------------------------

class TestT1ToolVersionPinning:
    def test_no_required_tools_is_skip(self):
        from exabench.cli.validators.t1_tool_versions import check_tool_version_pinning
        task = _make_task(required_tools=[])
        catalog = _make_catalog_mock([])
        result = check_tool_version_pinning(task, catalog)
        assert result.status == "SKIP"

    def test_all_tools_in_catalog_pass(self):
        from exabench.cli.validators.t1_tool_versions import check_tool_version_pinning
        task = _make_task(required_tools=["slurm_tool"])
        catalog = _make_catalog_mock(["slurm_tool"], version="2.0")
        result = check_tool_version_pinning(task, catalog)
        assert result.status == "PASS"

    def test_missing_tool_fails(self):
        from exabench.cli.validators.t1_tool_versions import check_tool_version_pinning
        task = _make_task(required_tools=["nonexistent_tool"])
        catalog = _make_catalog_mock(["slurm_tool"])
        result = check_tool_version_pinning(task, catalog)
        assert result.status == "FAIL"
        assert "nonexistent_tool" in result.detail

    def test_unknown_version_warns(self):
        from exabench.cli.validators.t1_tool_versions import check_tool_version_pinning
        task = _make_task(required_tools=["slurm_tool"])
        catalog = _make_catalog_mock(["slurm_tool"], version="unknown")
        result = check_tool_version_pinning(task, catalog)
        assert result.status == "WARN"


# ---------------------------------------------------------------------------
# T2: tool setup smoke test
# ---------------------------------------------------------------------------

class TestT2ToolSetup:
    def test_missing_snapshot_is_skip(self, tmp_path):
        from exabench.cli.validators.t2_tool_setup import check_tool_setup
        task = _make_task(required_tools=["slurm_tool"], snapshot_id="env_99")
        result = check_tool_setup(task, tmp_path)
        assert result.status == "SKIP"
        assert "not found" in result.detail

    def test_no_required_tools_is_skip(self, tmp_path):
        from exabench.cli.validators.t2_tool_setup import check_tool_setup
        env_dir = tmp_path / "env_01"
        env_dir.mkdir()
        task = _make_task(required_tools=[], snapshot_id="env_01")
        result = check_tool_setup(task, tmp_path)
        assert result.status == "SKIP"

    def test_snapshot_exists_with_data_dirs(self, tmp_path):
        from exabench.cli.validators.t2_tool_setup import check_tool_setup
        env_dir = tmp_path / "env_01"
        (env_dir / "slurm").mkdir(parents=True)
        task = _make_task(required_tools=["slurm_tool"], snapshot_id="env_01")
        # Should either PASS or FAIL (not SKIP)
        result = check_tool_setup(task, tmp_path)
        assert result.status in ("PASS", "FAIL", "WARN")


# ---------------------------------------------------------------------------
# T3: oracle solvability
# ---------------------------------------------------------------------------

class TestT3OracleSolvability:
    def test_missing_snapshot_is_skip(self, tmp_path):
        from exabench.cli.validators.t3_oracle_solvability import check_oracle_solvability
        task = _make_task(snapshot_id="env_99")
        result = check_oracle_solvability(task, tmp_path)
        assert result.status == "SKIP"

    def test_rubric_task_is_skip(self, tmp_path):
        from exabench.cli.validators.t3_oracle_solvability import check_oracle_solvability
        env_dir = tmp_path / "env_01"
        env_dir.mkdir()
        task = _make_task(scoring_mode="rubric", snapshot_id="env_01")
        result = check_oracle_solvability(task, tmp_path)
        assert result.status == "SKIP"

    def test_data_dirs_present_pass(self, tmp_path):
        from exabench.cli.validators.t3_oracle_solvability import check_oracle_solvability
        env_dir = tmp_path / "env_01"
        slurm_dir = env_dir / "slurm"
        slurm_dir.mkdir(parents=True)
        (slurm_dir / "jobs.json").write_text('{"jobs": []}')
        task = _make_task(data_type="job_ops", snapshot_id="env_01")
        result = check_oracle_solvability(task, tmp_path)
        assert result.status == "PASS"

    def test_missing_data_dir_fails(self, tmp_path):
        from exabench.cli.validators.t3_oracle_solvability import check_oracle_solvability
        env_dir = tmp_path / "env_01"
        env_dir.mkdir()
        task = _make_task(data_type="job_ops", snapshot_id="env_01")
        result = check_oracle_solvability(task, tmp_path)
        assert result.status == "FAIL"

    def test_derivation_query_success(self, tmp_path):
        from exabench.cli.validators.t3_oracle_solvability import check_oracle_solvability
        from exabench.schemas.task import HPCGroundTruth
        env_dir = tmp_path / "env_01"
        slurm_dir = env_dir / "slurm"
        slurm_dir.mkdir(parents=True)
        data = {"job_state": "FAILED", "job_id": 12345}
        (slurm_dir / "job_987654.json").write_text(json.dumps(data))
        gt = HPCGroundTruth(
            job_state="FAILED",
            derivation_query="slurm/job_987654.json:job_state",
        )
        task = _make_task(
            data_type="job_ops",
            snapshot_id="env_01",
            ground_truth=gt,
        )
        result = check_oracle_solvability(task, tmp_path)
        assert result.status == "PASS"

    def test_derivation_query_missing_file_fails(self, tmp_path):
        from exabench.cli.validators.t3_oracle_solvability import check_oracle_solvability
        from exabench.schemas.task import HPCGroundTruth
        env_dir = tmp_path / "env_01"
        env_dir.mkdir()
        gt = HPCGroundTruth(derivation_query="slurm/nonexistent.json:job_state")
        task = _make_task(
            data_type="job_ops",
            snapshot_id="env_01",
            ground_truth=gt,
        )
        result = check_oracle_solvability(task, tmp_path)
        assert result.status == "FAIL"


# ---------------------------------------------------------------------------
# T4: residual state policy
# ---------------------------------------------------------------------------

class TestT4ResidualState:
    def test_olap_task_passes(self):
        from exabench.cli.validators.t4_residual_state import check_residual_state_policy
        task = _make_task(workload_type="OLAP")
        result = check_residual_state_policy(task)
        assert result.status == "PASS"

    def test_oltp_task_warns(self):
        from exabench.cli.validators.t4_residual_state import check_residual_state_policy
        task = _make_task(workload_type="OLTP")
        result = check_residual_state_policy(task)
        assert result.status == "WARN"

    def test_oltp_write_task_warns(self):
        from exabench.cli.validators.t4_residual_state import check_residual_state_policy
        task = _make_task(task_id="write_job_123", workload_type="OLTP")
        result = check_residual_state_policy(task)
        assert result.status == "WARN"


# ---------------------------------------------------------------------------
# T5: GT isolation
# ---------------------------------------------------------------------------

class TestT5GTIsolation:
    def test_no_gt_is_skip(self, tmp_path):
        from exabench.cli.validators.t5_gt_isolation import check_ground_truth_isolation
        task = _make_task(ground_truth=None)
        catalog = _make_catalog_mock([])
        result = check_ground_truth_isolation(task, catalog, tmp_path)
        assert result.status == "SKIP"

    def test_missing_snapshot_is_skip(self, tmp_path):
        from exabench.cli.validators.t5_gt_isolation import check_ground_truth_isolation
        from exabench.schemas.task import HPCGroundTruth
        task = _make_task(snapshot_id="env_99", ground_truth=HPCGroundTruth(job_state="FAILED"))
        catalog = _make_catalog_mock([])
        result = check_ground_truth_isolation(task, catalog, tmp_path)
        assert result.status == "SKIP"

    def test_no_leakage_passes(self, tmp_path):
        from exabench.cli.validators.t5_gt_isolation import check_ground_truth_isolation
        from exabench.schemas.task import HPCGroundTruth
        env_dir = tmp_path / "env_01"
        docs_dir = env_dir / "docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "guide.json").write_text('{"topic": "SLURM guide"}')
        gt = HPCGroundTruth(job_state="FAILED")
        task = _make_task(snapshot_id="env_01", ground_truth=gt)
        catalog = _make_catalog_mock([])
        result = check_ground_truth_isolation(task, catalog, tmp_path)
        assert result.status == "PASS"


# ---------------------------------------------------------------------------
# T6: environment freeze
# ---------------------------------------------------------------------------

class TestT6EnvFreeze:
    def test_no_live_calls_passes(self, tmp_path):
        from exabench.cli.validators.t6_env_freeze import check_environment_freeze
        # The actual tool source dir is scanned; this test just checks it runs
        result = check_environment_freeze(tmp_path)
        assert result.status in ("PASS", "FAIL", "SKIP")

    def test_detects_requests_get(self, tmp_path):
        from exabench.cli.validators.t6_env_freeze import _scan_source
        source = 'response = requests.get("http://example.com/api")\n'
        violations = _scan_source(Path("fake_tool.py"), source)
        assert len(violations) == 1
        assert "requests.get" in violations[0]

    def test_detects_datetime_now(self, tmp_path):
        from exabench.cli.validators.t6_env_freeze import _scan_source
        source = "now = datetime.now()\n"
        violations = _scan_source(Path("fake_tool.py"), source)
        assert len(violations) == 1
        assert "datetime.now()" in violations[0]

    def test_ignores_comment_lines(self, tmp_path):
        from exabench.cli.validators.t6_env_freeze import _scan_source
        source = "# This would be requests.get(...) but it's a comment\n"
        violations = _scan_source(Path("fake_tool.py"), source)
        assert len(violations) == 0

    def test_clean_source_no_violations(self, tmp_path):
        from exabench.cli.validators.t6_env_freeze import _scan_source
        source = (
            "import json\n"
            "from pathlib import Path\n"
            "\ndef load(path):\n"
            "    return json.loads(Path(path).read_text())\n"
        )
        violations = _scan_source(Path("clean_tool.py"), source)
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# T7: GT correctness
# ---------------------------------------------------------------------------

class TestT7GTCorrectness:
    def test_rubric_task_is_skip(self, tmp_path):
        from exabench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
        task = _make_task(scoring_mode="rubric")
        result = check_ground_truth_correctness(task, tmp_path)
        assert result.status == "SKIP"

    def test_no_gt_is_skip(self, tmp_path):
        from exabench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
        task = _make_task(ground_truth=None)
        result = check_ground_truth_correctness(task, tmp_path)
        assert result.status == "SKIP"

    def test_missing_snapshot_is_skip(self, tmp_path):
        from exabench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
        from exabench.schemas.task import HPCGroundTruth
        task = _make_task(
            snapshot_id="env_99",
            ground_truth=HPCGroundTruth(job_state="FAILED"),
        )
        result = check_ground_truth_correctness(task, tmp_path)
        assert result.status == "SKIP"

    def test_no_derivation_query_warns(self, tmp_path):
        from exabench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
        from exabench.schemas.task import HPCGroundTruth
        env_dir = tmp_path / "env_01"
        env_dir.mkdir()
        gt = HPCGroundTruth(job_state="FAILED")
        task = _make_task(snapshot_id="env_01", ground_truth=gt)
        result = check_ground_truth_correctness(task, tmp_path)
        assert result.status == "WARN"

    def test_derivation_query_match_passes(self, tmp_path):
        from exabench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
        from exabench.schemas.task import HPCGroundTruth
        env_dir = tmp_path / "env_01"
        (env_dir / "slurm").mkdir(parents=True)
        data = {"job_state": "FAILED"}
        (env_dir / "slurm" / "job.json").write_text(json.dumps(data))
        gt = HPCGroundTruth(
            job_state="FAILED",
            derivation_query="slurm/job.json",
            comparison_mode="exact",
        )
        task = _make_task(snapshot_id="env_01", ground_truth=gt)
        result = check_ground_truth_correctness(task, tmp_path)
        assert result.status == "PASS"

    def test_derivation_query_mismatch_fails(self, tmp_path):
        from exabench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
        from exabench.schemas.task import HPCGroundTruth
        env_dir = tmp_path / "env_01"
        (env_dir / "slurm").mkdir(parents=True)
        data = {"job_state": "COMPLETED"}  # GT says FAILED
        (env_dir / "slurm" / "job.json").write_text(json.dumps(data))
        gt = HPCGroundTruth(
            job_state="FAILED",
            derivation_query="slurm/job.json",
            comparison_mode="exact",
        )
        task = _make_task(snapshot_id="env_01", ground_truth=gt)
        result = check_ground_truth_correctness(task, tmp_path)
        assert result.status == "FAIL"


# ---------------------------------------------------------------------------
# T8: task ambiguity
# ---------------------------------------------------------------------------

class TestT8Ambiguity:
    def test_deterministic_with_comparison_mode_passes(self):
        from exabench.cli.validators.t8_ambiguity import check_task_ambiguity
        from exabench.schemas.task import HPCGroundTruth
        gt = HPCGroundTruth(job_state="FAILED", comparison_mode="exact")
        task = _make_task(
            question="What is the state of job 123?",
            scoring_mode="deterministic",
            ground_truth=gt,
        )
        result = check_task_ambiguity(task)
        assert result.status == "PASS"

    def test_deterministic_without_comparison_mode_warns(self):
        from exabench.cli.validators.t8_ambiguity import check_task_ambiguity
        from exabench.schemas.task import HPCGroundTruth
        gt = HPCGroundTruth(job_state="FAILED")  # no comparison_mode
        task = _make_task(
            question="What is the state of job 123?",
            scoring_mode="deterministic",
            ground_truth=gt,
        )
        result = check_task_ambiguity(task)
        assert result.status == "WARN"

    def test_relative_time_without_anchor_warns(self):
        from exabench.cli.validators.t8_ambiguity import check_task_ambiguity
        task = _make_task(
            question="What jobs failed in the last 24 hours?",
            temporal_anchor=None,
        )
        result = check_task_ambiguity(task)
        assert result.status == "WARN"

    def test_relative_time_with_wrong_anchor_fails(self):
        from exabench.cli.validators.t8_ambiguity import check_task_ambiguity
        task = _make_task(
            question="What jobs failed recently?",
            temporal_anchor="system_clock",  # wrong value
        )
        result = check_task_ambiguity(task)
        assert result.status == "FAIL"

    def test_relative_time_with_correct_anchor_passes(self):
        from exabench.cli.validators.t8_ambiguity import check_task_ambiguity
        task = _make_task(
            question="What happened yesterday on node001?",
            temporal_anchor="snapshot_timestamp",
        )
        result = check_task_ambiguity(task)
        # Should PASS or WARN (only comparison_mode missing could cause WARN)
        assert result.status in ("PASS", "WARN")

    def test_rubric_without_rubric_id_warns(self):
        from exabench.cli.validators.t8_ambiguity import check_task_ambiguity
        task = _make_task(
            question="Explain the failure.",
            scoring_mode="rubric",
            rubric_id=None,
        )
        result = check_task_ambiguity(task)
        assert result.status == "WARN"


# ---------------------------------------------------------------------------
# T9: shortcut prevention
# ---------------------------------------------------------------------------

class TestT9Shortcuts:
    def test_small_corpus_is_skip(self):
        from exabench.cli.validators.t9_shortcuts import check_shortcut_prevention
        task = _make_task()
        result = check_shortcut_prevention(task, [task])
        assert result.status == "SKIP"

    def test_diverse_corpus_passes(self):
        from exabench.cli.validators.t9_shortcuts import check_shortcut_prevention
        from exabench.schemas.task import HPCGroundTruth
        tasks = [
            _make_task(
                task_id=f"task_{i:02d}",
                ground_truth=HPCGroundTruth(job_id=i * 1000),
            )
            for i in range(1, 11)
        ]
        result = check_shortcut_prevention(tasks[0], tasks)
        assert result.status == "PASS"

    def test_dominant_value_fails(self):
        from exabench.cli.validators.t9_shortcuts import check_shortcut_prevention
        from exabench.schemas.task import HPCGroundTruth
        # All 10 tasks share the same job_id
        tasks = [
            _make_task(
                task_id=f"task_{i:02d}",
                ground_truth=HPCGroundTruth(job_id=12345),
            )
            for i in range(10)
        ]
        result = check_shortcut_prevention(tasks[0], tasks)
        assert result.status == "FAIL"
        assert "12345" in result.detail


# ---------------------------------------------------------------------------
# T10: report generator
# ---------------------------------------------------------------------------

class TestT10Reporting:
    def _make_results(self):
        from exabench.cli.validators.base import CheckResult, TaskValidityResult
        return [
            TaskValidityResult(
                task_id="task_pass",
                overall="PASS",
                checks={"t1": CheckResult(status="PASS", detail="ok")},
            ),
            TaskValidityResult(
                task_id="task_warn",
                overall="WARN",
                checks={"t8": CheckResult(status="WARN", detail="no comparison_mode")},
            ),
            TaskValidityResult(
                task_id="task_fail",
                overall="FAIL",
                checks={"t3": CheckResult(status="FAIL", detail="snapshot missing")},
            ),
        ]

    def test_generates_report_dict(self):
        from exabench.cli.validators.t10_reporting import generate_validity_report
        results = self._make_results()
        report = generate_validity_report(results)
        assert report["summary"]["total_tasks"] == 3
        assert report["summary"]["pass"] == 1
        assert report["summary"]["warn"] == 1
        assert report["summary"]["fail"] == 1

    def test_corpus_valid_false_when_failures(self):
        from exabench.cli.validators.t10_reporting import generate_validity_report
        results = self._make_results()
        report = generate_validity_report(results, strict=False)
        assert report["corpus_valid"] is False

    def test_corpus_valid_true_when_only_warns(self):
        from exabench.cli.validators.base import CheckResult, TaskValidityResult
        from exabench.cli.validators.t10_reporting import generate_validity_report
        results = [
            TaskValidityResult(
                task_id="task_warn",
                overall="WARN",
                checks={"t8": CheckResult(status="WARN", detail="minor")},
            ),
        ]
        report = generate_validity_report(results, strict=False)
        assert report["corpus_valid"] is True

    def test_strict_mode_makes_warns_invalid(self):
        from exabench.cli.validators.base import CheckResult, TaskValidityResult
        from exabench.cli.validators.t10_reporting import generate_validity_report
        results = [
            TaskValidityResult(
                task_id="task_warn",
                overall="WARN",
                checks={"t8": CheckResult(status="WARN", detail="minor")},
            ),
        ]
        report = generate_validity_report(results, strict=True)
        assert report["corpus_valid"] is False

    def test_writes_json_to_file(self, tmp_path):
        from exabench.cli.validators.t10_reporting import generate_validity_report
        results = self._make_results()
        out_path = tmp_path / "report.json"
        generate_validity_report(results, output_path=out_path)
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert "summary" in data

    def test_text_format(self):
        from exabench.cli.validators.t10_reporting import format_text_report, generate_validity_report
        results = self._make_results()
        report = generate_validity_report(results)
        text = format_text_report(report)
        assert "PASS" in text
        assert "FAIL" in text
        assert "task_fail" in text

    def test_csv_format(self):
        from exabench.cli.validators.t10_reporting import format_csv_report, generate_validity_report
        results = self._make_results()
        report = generate_validity_report(results)
        csv_text = format_csv_report(report)
        lines = csv_text.strip().splitlines()
        assert len(lines) == 4  # header + 3 tasks
        assert "task_id" in lines[0]


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

class TestValidateTasksCLI:
    def test_missing_task_file_returns_error(self, tmp_path):
        from exabench.cli.validate_tasks import main
        ret = main([
            "--task-file", str(tmp_path / "nonexistent.json"),
        ])
        assert ret == 1

    def test_runs_on_real_task_file(self):
        """Integration smoke test: runs against the real task corpus."""
        task_file = Path("benchmark/tasks/task_set_v1.json")
        if not task_file.exists():
            pytest.skip("task_set_v1.json not found")

        from exabench.cli.validate_tasks import main
        # Run only T4 and T8 (pure schema checks, no I/O)
        ret = main([
            "--task-file", str(task_file),
            "--checks", "t4,t8",
            "--format", "text",
        ])
        # May PASS or FAIL depending on task content; just check it runs
        assert ret in (0, 1)


class TestAuditScorersCLI:
    def test_missing_task_file_returns_error(self, tmp_path):
        from exabench.cli.audit_scorers import main
        ret = main([
            "--task-file", str(tmp_path / "nonexistent.json"),
        ])
        assert ret == 1

    def test_runs_on_real_task_file(self):
        """Integration smoke test: runs against the real task corpus."""
        task_file = Path("benchmark/tasks/task_set_v1.json")
        if not task_file.exists():
            pytest.skip("task_set_v1.json not found")

        from exabench.cli.audit_scorers import main
        # Run only O.b (negation check — no YAML file needed)
        ret = main([
            "--task-file", str(task_file),
            "--check", "ob",
            "--format", "text",
        ])
        assert ret in (0, 1)

    def test_invalid_check_name_defaults_to_all(self, tmp_path):
        from exabench.cli.audit_scorers import _resolve_checks
        result = _resolve_checks("invalid_check")
        assert result == ["oa", "ob", "oc"]  # fallback to all


# ---------------------------------------------------------------------------
# String equivalence helpers (audit_scorers internals)
# ---------------------------------------------------------------------------

class TestAuditScorerHelpers:
    def test_normalise(self):
        from exabench.cli.audit_scorers import _normalise
        assert _normalise("  FAILED  ") == "failed"
        assert _normalise("512 GB") == "512 gb"

    def test_negate_slurm_states(self):
        from exabench.cli.audit_scorers import _negate_value
        assert _negate_value("FAILED") == "COMPLETED"
        assert _negate_value("COMPLETED") == "FAILED"
        assert _negate_value("RUNNING") == "PENDING"

    def test_negate_numeric(self):
        from exabench.cli.audit_scorers import _negate_value
        result = _negate_value("42")
        assert result == "43"

    def test_simple_match_score(self):
        from exabench.cli.audit_scorers import _simple_match_score
        assert _simple_match_score("FAILED", "FAILED") == 1.0
        assert _simple_match_score("COMPLETED", "FAILED") == 0.0

    def test_deterministic_score_exact(self):
        from exabench.cli.audit_scorers import _deterministic_score
        gt = {"job_state": "FAILED", "exit_code": "137"}
        pred = {"job_state": "FAILED", "exit_code": "137"}
        assert _deterministic_score(pred, gt) == 1.0

    def test_deterministic_score_partial(self):
        from exabench.cli.audit_scorers import _deterministic_score
        gt = {"job_state": "FAILED", "exit_code": "137"}
        pred = {"job_state": "FAILED", "exit_code": "1"}  # exit code wrong
        score = _deterministic_score(pred, gt)
        assert 0.0 < score < 1.0
