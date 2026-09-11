"""Tests for ``aobench review task``.

The command's value is that its verdicts are trustworthy, so these tests are mostly about
the boundary between FAIL and WARN. A checker that cries FAIL on work a reviewer already
accepted teaches people to ignore it, which is worse than not having it.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from aobench.cli.main import app
from aobench.cli.review_cmd import _check_evidence, _check_tools, _check_unfinished

runner = CliRunner()


def _status(payload: str, item: str) -> str:
    checks = json.loads(payload)["checks"]
    return next(c["status"] for c in checks if c["item"] == item)


def _write(tmp_path, **overrides):
    spec = {
        "task_id": "DOCS_DES_900",
        "title": "A real title",
        "query_text": "A real question?",
        "role": "system_designer",
        "qcat": "DOCS",
        "difficulty": "medium",
        "difficulty_tier": 2,
        "environment_id": "env_23",
        "expected_answer_type": "lookup",
        "gold_evidence_refs": ["docs/architecture_spec.md"],
        "eval_criteria": {"evaluation_mode": "semantic_match", "gold_answer": "An answer."},
        "allowed_tools": ["docs"],
        "validation_status": "validated",
    }
    spec.update(overrides)
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- unfinished


def test_scaffold_markers_report_todo_not_fail():
    # A half-written task is not a broken one. Failing it would make `review` useless as
    # the tool an author runs *while* writing.
    check = _check_unfinished(
        {
            "title": "TODO: something",
            "query_text": "real",
            "eval_criteria": {"gold_answer": "real"},
        }
    )
    assert check.status == "TODO"
    assert "title" in check.detail


def test_not_started_status_reports_todo():
    check = _check_unfinished(
        {
            "title": "real",
            "query_text": "real",
            "eval_criteria": {"gold_answer": "real"},
            "validation_status": "not_started",
        }
    )
    assert check.status == "TODO"


def test_finished_task_passes():
    check = _check_unfinished(
        {
            "title": "real",
            "query_text": "real",
            "eval_criteria": {"gold_answer": "real"},
            "validation_status": "validated",
        }
    )
    assert check.status == "PASS"


# --------------------------------------------------------------------------- evidence


def test_missing_evidence_file_is_a_failure(tmp_path):
    (tmp_path / "docs").mkdir()
    check = _check_evidence({"gold_evidence_refs": ["docs/nope.md"]}, tmp_path)
    assert check.status == "FAIL"


def test_evidence_anchor_fragment_is_stripped_before_the_existence_check(tmp_path):
    (tmp_path / "slurm").mkdir()
    (tmp_path / "slurm" / "job_details.json").write_text("{}", encoding="utf-8")
    check = _check_evidence(
        {"gold_evidence_refs": ["slurm/job_details.json#oom_evidence"]}, tmp_path
    )
    assert check.status == "PASS"


def test_required_evidence_must_also_be_listed_as_gold_evidence(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("x", encoding="utf-8")
    check = _check_evidence(
        {
            "gold_evidence_refs": ["docs/a.md"],
            "eval_criteria": {"required_evidence_refs": ["docs/b.md"]},
        },
        tmp_path,
    )
    assert check.status == "FAIL"
    assert "docs/b.md" in check.detail


# --------------------------------------------------------------------------- tools / RBAC


def _policy(tmp_path, role: str, allowed) -> None:
    policy_dir = tmp_path / "policy"
    policy_dir.mkdir(exist_ok=True)
    body = {"roles": {role: {}}}
    if allowed is not None:
        body["roles"][role]["allowed_tools"] = allowed
    (policy_dir / "rbac_policy.yaml").write_text(json.dumps(body), encoding="utf-8")


def test_unknown_tool_family_is_a_failure(tmp_path):
    check = _check_tools({"allowed_tools": ["wormhole"], "role": "sysadmin"}, tmp_path)
    assert check.status == "FAIL"
    assert "wormhole" in check.detail


def test_wildcard_in_the_policy_permits_everything(tmp_path):
    # `allowed_tools: ['*']` appears in 15 of the bundles. Reading it as a literal tool name
    # made every task in those bundles look like an over-grant.
    _policy(tmp_path, "facility_admin", ["*"])
    check = _check_tools(
        {"allowed_tools": ["slurm", "telemetry"], "role": "facility_admin"}, tmp_path
    )
    assert check.status == "PASS"


def test_policy_silent_about_a_role_is_skipped_not_failed(tmp_path):
    # 12 role entries omit allowed_tools entirely. Absence of a statement is not a denial.
    _policy(tmp_path, "sysadmin", None)
    check = _check_tools({"allowed_tools": ["slurm"], "role": "sysadmin"}, tmp_path)
    assert check.status == "SKIP"


def test_over_grant_warns_rather_than_fails(tmp_path):
    # ToolRegistry gates on the task's allowed_tools alone and never intersects it with this
    # policy, so an over-grant is a question for a reviewer, not a proven defect. 10 tasks
    # already in the corpus trip this.
    _policy(tmp_path, "scientific_user", ["slurm", "docs"])
    check = _check_tools(
        {"allowed_tools": ["slurm", "telemetry"], "role": "scientific_user"}, tmp_path
    )
    assert check.status == "WARN"
    assert "telemetry" in check.detail


def test_tools_within_policy_pass(tmp_path):
    _policy(tmp_path, "scientific_user", ["slurm", "docs"])
    check = _check_tools({"allowed_tools": ["slurm"], "role": "scientific_user"}, tmp_path)
    assert check.status == "PASS"


def test_missing_policy_file_is_skipped(tmp_path):
    check = _check_tools({"allowed_tools": ["slurm"], "role": "sysadmin"}, tmp_path)
    assert check.status == "SKIP"


# --------------------------------------------------------------------------- the command


def test_reviewing_a_real_corpus_task_does_not_fail():
    # The whole corpus was reviewed by a human already; a checker that fails it is wrong.
    result = runner.invoke(app, ["review", "task", "JOB_USR_001", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["failed"] == 0


# Tasks that already fail the mechanical review on `main`. Every one of them grants a tool
# family that does not exist -- `topology`, `inventory`, `filesystem` -- so ToolRegistry
# silently drops it (`available_tool_names` is `_allowed & _tools`). Three of them end up
# handing the agent NO tools at all while still expecting evidence from a topology file.
#
# This is a ratchet, not an allowance: the list must only ever shrink. A new task that
# fails review breaks this test, which is the point.
_KNOWN_FAILING = {
    "ARCH_DES_001",
    "ARCH_FAC_001",
    "ARCH_RES_001",
    "ARCH_SYS_001",
    "ARCH_USR_001",
    "DATA_DES_001",
    "DATA_FAC_001",
    "DATA_RES_001",
    "DATA_SYS_001",
    "DATA_USR_001",
}


def test_no_new_task_fails_the_mechanical_checks():
    from aobench.cli._common import available_task_ids, resolve_root

    root = resolve_root("benchmark")
    failing = set()
    for task_id in available_task_ids(root):
        result = runner.invoke(app, ["review", "task", task_id, "--json"])
        if result.exit_code != 0:
            failing.add(task_id)

    new_failures = failing - _KNOWN_FAILING
    assert not new_failures, f"these tasks newly fail review: {sorted(new_failures)}"

    fixed = _KNOWN_FAILING - failing
    assert not fixed, (
        f"these tasks now pass review: {sorted(fixed)} — remove them from _KNOWN_FAILING "
        "so the ratchet keeps holding"
    )


def test_the_known_failures_all_share_one_cause():
    # If this ever fails, the list above has grown a second meaning and needs splitting.
    for task_id in sorted(_KNOWN_FAILING):
        result = runner.invoke(app, ["review", "task", task_id, "--json"])
        tools = next(c for c in json.loads(result.output)["checks"] if c["item"] == "Tools")
        assert tools["status"] == "FAIL"
        assert "unknown tool famil" in tools["detail"], f"{task_id}: {tools['detail']}"


def test_a_broken_environment_reference_fails(tmp_path):
    spec = _write(tmp_path, environment_id="env_does_not_exist")
    result = runner.invoke(app, ["review", "task", str(spec), "--json"])
    assert result.exit_code == 1
    assert _status(result.output, "Environment") == "FAIL"


def test_schema_violation_fails(tmp_path):
    spec = _write(tmp_path, qcat="NOT_A_QCAT")
    result = runner.invoke(app, ["review", "task", str(spec), "--json"])
    assert result.exit_code == 1
    assert _status(result.output, "Schema") == "FAIL"


def test_unknown_task_id_exits_with_suggestions():
    result = runner.invoke(app, ["review", "task", "JOB_USR_99999"])
    assert result.exit_code != 0


def test_json_output_is_machine_readable(tmp_path):
    spec = _write(tmp_path)
    result = runner.invoke(app, ["review", "task", str(spec), "--json"])
    payload = json.loads(result.output)
    assert payload["task_id"] == "DOCS_DES_900"
    assert payload["ok"] is True
    assert {c["item"] for c in payload["checks"]} == {
        "Schema",
        "Finished",
        "Environment",
        "Evidence",
        "Tools",
        "Scoring",
        "Coverage",
    }


def test_a_scaffold_reviews_clean_apart_from_its_todos(tmp_path):
    # The two commands are one workflow: `new task` then `review task` should tell the
    # author what is left, not bury them in failures.
    dest = tmp_path / "scaffold.json"
    assert runner.invoke(app, ["new", "task", "--cell", "DOCS_DES", "-o", str(dest)]).exit_code == 0

    result = runner.invoke(app, ["review", "task", str(dest), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["failed"] == 0
    assert _status(result.output, "Finished") == "TODO"
