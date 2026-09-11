"""Tests for ``aobench new task``.

The command's whole purpose is that what it emits is *immediately valid*, so the tests
that matter most are the ones that parse its output back through ``TaskSpec`` rather than
string-matching the terminal. The id-allocation and cell-resolution tests exist because
both encode corpus conventions that live nowhere else in code.
"""

from __future__ import annotations

import json

import pytest
import typer
from typer.testing import CliRunner

from aobench.cli.main import app
from aobench.cli.new_cmd import _next_task_id, _resolve_cell, _thinnest_cell
from aobench.schemas.task import TaskSpec

runner = CliRunner()


# --------------------------------------------------------------------------- helpers


def _spec(task_id: str, qcat: str, role: str) -> dict[str, str]:
    return {"task_id": task_id, "qcat": qcat, "role": role, "environment_id": "env_01"}


# --------------------------------------------------------------------------- id allocation


def test_next_task_id_starts_at_001_for_an_empty_cell():
    assert _next_task_id([], "DOCS", "DES") == "DOCS_DES_001"


def test_next_task_id_continues_after_the_highest_existing():
    specs = [_spec("DOCS_DES_001", "DOCS", "system_designer")]
    assert _next_task_id(specs, "DOCS", "DES") == "DOCS_DES_002"


def test_next_task_id_fills_a_gap_left_by_a_removed_task():
    # 002 was withdrawn. Reusing the id would silently alias it in any published result
    # that still references it, so the allocator takes the lowest free number on purpose.
    specs = [
        _spec("DOCS_DES_001", "DOCS", "system_designer"),
        _spec("DOCS_DES_003", "DOCS", "system_designer"),
    ]
    assert _next_task_id(specs, "DOCS", "DES") == "DOCS_DES_002"


def test_next_task_id_ignores_the_m100_prefixed_namespace():
    # M100_JOB_USR_001 must not be mistaken for JOB_USR_001 — different corpus namespace.
    specs = [_spec("M100_JOB_USR_001", "JOB", "scientific_user")]
    assert _next_task_id(specs, "JOB", "USR") == "JOB_USR_001"


def test_next_task_id_ignores_other_cells():
    specs = [_spec("JOB_SYS_001", "JOB", "sysadmin")]
    assert _next_task_id(specs, "JOB", "USR") == "JOB_USR_001"


# --------------------------------------------------------------------------- cell resolution


def test_resolve_cell_accepts_the_cell_shorthand():
    assert _resolve_cell("DOCS_DES", None, None) == ("DOCS", "system_designer")


def test_resolve_cell_accepts_a_role_code_or_a_role_name():
    assert _resolve_cell(None, "DOCS", "DES") == ("DOCS", "system_designer")
    assert _resolve_cell(None, "DOCS", "system_designer") == ("DOCS", "system_designer")


def test_resolve_cell_handles_a_qcat_containing_no_underscore_ambiguity():
    # rpartition, not partition: the role code is the LAST segment.
    assert _resolve_cell("ENERGY_FAC", None, None) == ("ENERGY", "facility_admin")


@pytest.mark.parametrize(
    "cell,qcat,role",
    [
        ("DOCSDES", None, None),  # no separator
        (None, "NOPE", "DES"),  # unknown qcat
        (None, "DOCS", "wizard"),  # unknown role
        (None, None, None),  # nothing given
        ("DOCS_DES", "DOCS", None),  # both forms at once
    ],
)
def test_resolve_cell_rejects_bad_input(cell, qcat, role):
    with pytest.raises(typer.Exit):
        _resolve_cell(cell, qcat, role)


def test_thinnest_cell_prefers_the_emptiest_and_breaks_ties_deterministically():
    specs = [_spec(f"AIOPS_USR_{i:03d}", "AIOPS", "scientific_user") for i in range(3)]
    first = _thinnest_cell(specs)
    assert first == _thinnest_cell(specs), "must be stable across calls"
    assert first != ("AIOPS", "scientific_user"), "the populated cell is not the thinnest"


# --------------------------------------------------------------------------- the command


def test_dry_run_emits_a_spec_that_taskspec_accepts():
    result = runner.invoke(app, ["new", "task", "--cell", "DOCS_DES", "--dry-run"])
    assert result.exit_code == 0, result.output
    payload = result.output[result.output.index("{") :]
    TaskSpec.model_validate(json.loads(payload))


def test_dry_run_writes_nothing(tmp_path):
    before = sorted(tmp_path.iterdir())
    result = runner.invoke(
        app, ["new", "task", "--cell", "DOCS_DES", "--dry-run", "-o", str(tmp_path / "x.json")]
    )
    assert result.exit_code == 0
    assert sorted(tmp_path.iterdir()) == before


def test_written_spec_is_valid_and_marked_unfinished(tmp_path):
    dest = tmp_path / "scaffold.json"
    result = runner.invoke(app, ["new", "task", "--cell", "DOCS_DES", "-o", str(dest)])
    assert result.exit_code == 0, result.output

    spec = TaskSpec.model_validate(json.loads(dest.read_text(encoding="utf-8")))
    assert spec.qcat == "DOCS"
    assert spec.role == "system_designer"
    # A scaffold must announce that it is not a finished task, or it looks like a reviewed
    # one that nobody checked.
    assert spec.validation_status == "not_started"
    assert spec.scoring_readiness == "blocked"


def test_the_value_bearing_fields_are_left_as_todo(tmp_path):
    # Generating a plausible gold answer would be worse than leaving it blank: a benchmark
    # whose answers were written by a model measures the model, not the agent.
    dest = tmp_path / "scaffold.json"
    runner.invoke(app, ["new", "task", "--cell", "DOCS_DES", "-o", str(dest)])
    raw = json.loads(dest.read_text(encoding="utf-8"))

    assert "TODO" in raw["query_text"]
    assert "TODO" in raw["title"]
    assert "TODO" in raw["eval_criteria"]["gold_answer"]
    assert raw["gold_evidence_refs"] == []


def test_difficulty_sets_the_matching_tier(tmp_path):
    dest = tmp_path / "hard.json"
    runner.invoke(
        app, ["new", "task", "--cell", "DOCS_DES", "--difficulty", "hard", "-o", str(dest)]
    )
    raw = json.loads(dest.read_text(encoding="utf-8"))
    assert raw["difficulty"] == "hard"
    assert raw["difficulty_tier"] == 3


def test_refuses_to_overwrite_without_force(tmp_path):
    dest = tmp_path / "taken.json"
    dest.write_text("keep me", encoding="utf-8")

    result = runner.invoke(app, ["new", "task", "--cell", "DOCS_DES", "-o", str(dest)])
    assert result.exit_code == 1
    assert dest.read_text(encoding="utf-8") == "keep me"

    forced = runner.invoke(app, ["new", "task", "--cell", "DOCS_DES", "-o", str(dest), "--force"])
    assert forced.exit_code == 0
    assert dest.read_text(encoding="utf-8") != "keep me"


def test_unknown_environment_is_rejected_before_anything_is_written(tmp_path):
    dest = tmp_path / "never.json"
    result = runner.invoke(
        app, ["new", "task", "--cell", "DOCS_DES", "--env", "env_999", "-o", str(dest)]
    )
    assert result.exit_code == 2
    assert not dest.exists()


def test_thinnest_reports_the_cell_it_chose():
    result = runner.invoke(app, ["new", "task", "--thinnest", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Thinnest cell:" in result.output


def test_thinnest_conflicts_with_an_explicit_cell():
    result = runner.invoke(app, ["new", "task", "--thinnest", "--cell", "DOCS_DES"])
    assert result.exit_code == 2


def test_output_lists_real_evidence_files_from_the_chosen_snapshot(tmp_path):
    # The point of the listing is that an author does not have to go exploring the bundle
    # by hand, so it must name files that genuinely exist.
    result = runner.invoke(
        app,
        ["new", "task", "--cell", "DOCS_DES", "--env", "env_23", "-o", str(tmp_path / "s.json")],
    )
    assert result.exit_code == 0, result.output
    assert "Evidence available in env_23" in result.output
    assert "policy/rbac_policy.yaml" in result.output
