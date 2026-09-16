"""Regression coverage for scored batch-run readiness gating."""

from __future__ import annotations

from aobench.cli.run_cmd import _is_run_ready, _load_split_ids
from aobench.schemas.task import TaskSpec


def _task(*, task_id: str, scoring_readiness: str) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        title="T",
        query_text="Q",
        role="scientific_user",
        qcat="DOCS",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="diagnosis",
        scoring_readiness=scoring_readiness,
    )


def test_is_run_ready_only_accepts_ready_tasks():
    assert _is_run_ready(_task(task_id="DOCS_USR_001", scoring_readiness="ready")) is True
    assert _is_run_ready(_task(task_id="DOCS_USR_002", scoring_readiness="partial")) is True
    assert _is_run_ready(_task(task_id="DOCS_USR_003", scoring_readiness="blocked")) is False


def test_dev_split_excludes_non_ready_scaffolds():
    split_ids = _load_split_ids(
        "dev",
        "/Users/bytedance/Trae/GitHub热点日报/repos/aobench-fix75/benchmark",
    )
    assert split_ids is not None
    assert "DOCS_DES_002" not in split_ids
    assert "JOB_RES_001" in split_ids
    assert "DOCS_USR_001" in split_ids
