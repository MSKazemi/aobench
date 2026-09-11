"""Tests for ``scripts/review_changed_tasks.py``.

This script is a CI gate, so the behaviour worth pinning is which outcomes *block*. A gate
that blocks on a judgement call teaches contributors to route around it, and a gate that
lets a real failure through is worse than none.

The rendering is exercised through the real report shape rather than a hand-built string,
because the shape is a contract with ``aobench review task --json``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "review_changed_tasks.py"


def _load():
    spec = importlib.util.spec_from_file_location("review_changed_tasks", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load()


def _report(task_id: str, *statuses: str) -> dict:
    return {
        "task_id": task_id,
        "checks": [
            {"item": f"Check{i}", "status": s, "detail": "detail"}
            for i, s in enumerate(statuses)
        ],
        "_blocking": any(s == "FAIL" for s in statuses),
    }


# --------------------------------------------------------------------------- what blocks


def test_only_fail_is_treated_as_blocking(mod):
    assert mod._BLOCKING == {"FAIL"}


@pytest.mark.parametrize("status", ["WARN", "TODO", "SKIP", "PASS"])
def test_non_fail_statuses_do_not_block(mod, status):
    # An over-grant of tools is a WARN and a scaffold is a TODO. Blocking a PR on either
    # would make the gate an obstacle rather than a review aid.
    assert status not in mod._BLOCKING


# --------------------------------------------------------------------------- rendering


def test_render_names_the_failing_task_and_counts_it(mod):
    out = mod._render([_report("A", "PASS"), _report("B", "PASS", "FAIL")])
    assert "1 of 2 changed task(s) have a blocking failure" in out
    assert "`B`" in out


def test_render_says_what_is_left_when_nothing_blocks(mod):
    out = mod._render([_report("A", "PASS", "WARN")])
    assert "pass the mechanical checks" in out
    assert "needs a human" in out


def test_render_always_states_what_the_check_cannot_decide(mod):
    # The point of the gate is to hand the human back the two questions only they can
    # answer; if that text ever disappears the gate starts reading like an approval.
    out = mod._render([_report("A", "PASS")])
    assert "Is the gold answer right?" in out
    assert "question the role would really ask" in out


def test_render_escapes_pipes_so_a_detail_cannot_break_the_table(mod):
    report = _report("A", "WARN")
    report["checks"][0]["detail"] = "grants a|b|c"
    out = mod._render([report])
    assert r"grants a\|b\|c" in out


def test_render_marks_every_status_distinctly(mod):
    # Five statuses sharing an icon would make the summary unreadable at a glance.
    assert len(set(mod._ICON.values())) == len(mod._ICON)


# --------------------------------------------------------------------------- path filtering


def test_only_task_specs_are_reviewed(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod.sys, "argv", ["prog", "README.md", "src/aobench/cli/main.py"])
    assert mod.main() == 0
    assert "nothing to review" in capsys.readouterr().out


def test_a_broken_base_ref_fails_loudly_instead_of_reporting_a_clean_run(mod, monkeypatch, capsys):
    # "nothing changed" and "I could not tell what changed" must not look the same to a
    # gate: swallowing the diff error would turn a misconfigured base into a silent pass.
    monkeypatch.setattr(mod.sys, "argv", ["prog", "--base", "origin/no-such-branch"])
    assert mod.main() == 2
    assert "could not determine what changed" in capsys.readouterr().err


def test_diff_failure_raises_rather_than_returning_empty(mod):
    with pytest.raises(mod.DiffFailed):
        mod._changed_specs("origin/definitely-not-a-branch")


def test_no_changed_specs_is_success_not_an_error(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_changed_specs", lambda base: [])
    monkeypatch.setattr(mod.sys, "argv", ["prog"])
    assert mod.main() == 0
    assert "nothing to review" in capsys.readouterr().out


# --------------------------------------------------------------------------- end to end


def test_a_healthy_corpus_task_does_not_block(mod, monkeypatch):
    monkeypatch.setattr(
        mod.sys, "argv", ["prog", "benchmark/tasks/specs/JOB_USR_001.json"]
    )
    assert mod.main() == 0


def test_a_task_with_a_nonexistent_tool_family_blocks(mod, monkeypatch):
    # ARCH_RES_001 grants `topology`, which no tool provides. See
    # tests/unit/test_review_cmd.py::_KNOWN_FAILING for the full set and why it exists.
    monkeypatch.setattr(
        mod.sys, "argv", ["prog", "benchmark/tasks/specs/ARCH_RES_001.json"]
    )
    assert mod.main() == 1


def test_the_step_summary_is_written_when_github_sets_it(mod, monkeypatch, tmp_path):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(
        mod.sys, "argv", ["prog", "benchmark/tasks/specs/JOB_USR_001.json"]
    )
    assert mod.main() == 0
    assert "## Corpus review" in summary.read_text(encoding="utf-8")


def test_nothing_is_written_when_github_step_summary_is_unset(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(
        mod.sys, "argv", ["prog", "benchmark/tasks/specs/JOB_USR_001.json"]
    )
    assert mod.main() == 0  # must not raise for want of the env var
