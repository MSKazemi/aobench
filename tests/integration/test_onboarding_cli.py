"""Integration tests for the first-use surface: quickstart, doctor, info, list.

These commands are what a brand-new user touches first, so the properties under test
are the onboarding promises themselves: they work with zero arguments, they work from
an arbitrary working directory (the corpus is resolved, never assumed to be `./benchmark`),
a mistyped ID produces a suggestion rather than a traceback, and a missing optional
extra never fails the command.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aobench.cli.main import app

runner = CliRunner()

pytestmark = pytest.mark.usefixtures("_cwd_outside_checkout")


@pytest.fixture
def _cwd_outside_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, benchmark_root: Path):
    """Run each test from a scratch directory with no ``benchmark/`` above it.

    This is the installed-wheel situation. Without the explicit env var the resolver
    would have to fall back to package data, which is only populated in a built wheel,
    so point it at the repository corpus instead.
    """
    monkeypatch.setenv("AOBENCH_BENCHMARK_ROOT", str(benchmark_root))
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def test_doctor_passes_on_a_healthy_install() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "AOBench looks healthy" in result.output


def test_doctor_exit_code_ignores_missing_optional_extras(monkeypatch: pytest.MonkeyPatch) -> None:
    """A laptop with no provider SDKs installed must still exit 0."""
    from aobench.cli import info_cmd

    optional = {name for name, _, _ in info_cmd._OPTIONAL_DEPS}
    real = info_cmd._installed
    monkeypatch.setattr(
        info_cmd, "_installed", lambda name: False if name in optional else real(name)
    )
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "WARN" in result.output


def test_doctor_fails_when_the_corpus_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing corpus is a required failure — and must not reclassify the extras.

    Regression guard: the required/optional split used to be positional, so the four
    checks that disappear when the corpus is absent caused optional extras to be
    counted as required failures.
    """
    monkeypatch.setenv("AOBENCH_BENCHMARK_ROOT", "/nonexistent/benchmark")
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1, result.output
    assert "1 required check(s) failed" in result.output


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


def test_info_json_is_parseable_and_reports_the_corpus() -> None:
    result = runner.invoke(app, ["info", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["corpus"]["tasks"] > 0
    assert payload["corpus"]["environments"] > 0
    assert "aobench_version" in payload


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_list_tasks_from_outside_a_checkout() -> None:
    result = runner.invoke(app, ["list", "tasks"])
    assert result.exit_code == 0, result.output
    assert "JOB_USR_001" in result.output


def test_list_tasks_filters_compose() -> None:
    result = runner.invoke(app, ["list", "tasks", "--qcat", "JOB", "--role", "sysadmin", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert rows, "expected at least one JOB/sysadmin task"
    assert all(r["qcat"] == "JOB" and r["role"] == "sysadmin" for r in rows)


def test_list_tasks_ids_only_emits_bare_ids() -> None:
    result = runner.invoke(app, ["list", "tasks", "--ids-only"])
    assert result.exit_code == 0, result.output
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert lines
    assert all(" " not in ln for ln in lines)


def test_list_envs_reports_grounding() -> None:
    result = runner.invoke(app, ["list", "envs", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert {"synthetic", "real-M100"} >= {r["grounding"] for r in rows}


def test_list_adapters_needs_no_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Adapter discovery must work even before the corpus resolves."""
    monkeypatch.setenv("AOBENCH_BENCHMARK_ROOT", "/nonexistent/benchmark")
    result = runner.invoke(app, ["list", "adapters"])
    assert result.exit_code == 0, result.output
    assert "direct_qa" in result.output


def test_list_coverage_totals_match_the_corpus_size() -> None:
    result = runner.invoke(app, ["list", "coverage", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    tasks_result = runner.invoke(app, ["list", "tasks", "--json"])
    corpus_size = len(json.loads(tasks_result.output))

    assert payload["total_tasks"] == corpus_size
    assert sum(row["total"] for row in payload["qcat_role_counts"]) == corpus_size
    assert len(payload["qcat_role_counts"]) == 10  # every QCAT gets a row, even if thin


def test_list_coverage_json_matches_the_table() -> None:
    json_result = runner.invoke(app, ["list", "coverage", "--json"])
    table_result = runner.invoke(app, ["list", "coverage"])
    assert json_result.exit_code == 0, json_result.output
    assert table_result.exit_code == 0, table_result.output

    payload = json.loads(json_result.output)
    for row in payload["qcat_role_counts"]:
        assert row["qcat"] in table_result.output
        assert str(row["total"]) in table_result.output


def test_list_coverage_calls_out_thin_cells() -> None:
    result = runner.invoke(app, ["list", "coverage", "--json"])
    payload = json.loads(result.output)
    assert payload["thin_cells"], "expected at least one thin cell in the current corpus"
    for cell in payload["thin_cells"]:
        qcat, code = cell.rsplit("_", 1)
        row = next(r for r in payload["qcat_role_counts"] if r["qcat"] == qcat)
        assert row[code] <= 1


def test_list_coverage_m100_subset_matches_grounded_task_count() -> None:
    """Cross-check against ``list tasks --grounded`` rather than a hardcoded count.

    The corpus grows as contributors add tasks (CONTRIBUTING.md invites exactly that),
    so this must hold for whatever the M100-grounded count happens to be, not today's 8.
    """
    coverage_result = runner.invoke(app, ["list", "coverage", "--json"])
    grounded_result = runner.invoke(app, ["list", "tasks", "--grounded", "--json"])
    payload = json.loads(coverage_result.output)
    grounded_count = len(json.loads(grounded_result.output))

    assert sum(row["total"] for row in payload["m100_grounded_counts"]) == grounded_count
    assert payload["m100_grounded_total"] == grounded_count


def test_list_coverage_counts_tasks_with_an_unknown_qcat_or_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No task may be dropped from the matrix for carrying an unrecognised qcat/role.

    The header states the corpus size, so a task the axes do not recognise must widen
    the matrix rather than disappear from it -- otherwise ``list coverage`` under-reports
    coverage while claiming to be complete, which is the one thing this command exists
    to get right. CONTRIBUTING.md actively invites new tasks, so an unfamiliar qcat or a
    typo'd role is a matter of time; judging whether the value is *legal* is the job of
    ``aobench validate benchmark``, not of a read-only listing.
    """
    spec_dir = tmp_path / "tasks" / "specs"
    spec_dir.mkdir(parents=True)
    for task_id, qcat, role in [
        ("JOB_USR_001", "JOB", "scientific_user"),
        ("NEWQ_USR_001", "NEWQ", "scientific_user"),  # qcat not in _QCAT_DESCRIPTIONS
        ("JOB_OPS_001", "JOB", "ml_engineer"),  # role not in _ROLE_CODES
        ("BLANK_001", "", ""),  # neither field usable
    ]:
        (spec_dir / f"{task_id}.json").write_text(
            json.dumps({"task_id": task_id, "qcat": qcat, "role": role})
        , encoding="utf-8")

    monkeypatch.setenv("AOBENCH_BENCHMARK_ROOT", str(tmp_path))
    payload = json.loads(runner.invoke(app, ["list", "coverage", "--json"]).output)

    assert payload["total_tasks"] == 4
    assert sum(row["total"] for row in payload["qcat_role_counts"]) == 4

    by_qcat = {row["qcat"]: row for row in payload["qcat_role_counts"]}
    assert by_qcat["NEWQ"]["USR"] == 1, "an unknown qcat must get its own row"
    assert by_qcat["JOB"]["ML_ENGINEER"] == 1, "an unknown role must get its own column"
    assert by_qcat["(unset)"]["(UNSET)"] == 1, "a blank qcat/role must still be counted"

    # The documented QCATs stay present even with nothing in them, and an empty cell is
    # reported as a gap rather than folded in with the merely-thin ones.
    assert by_qcat["ENERGY"]["total"] == 0
    assert "ENERGY_FAC" in payload["empty_cells"]
    assert set(payload["empty_cells"]) <= set(payload["thin_cells"])


def test_list_coverage_help_renders() -> None:
    """`--help` must render, which is what catches a malformed Typer signature.

    Deliberately no assertion on the rendered text: Typer draws help through rich, and
    when colour is enabled (as it is on CI) the option names carry interleaved ANSI
    escapes, so even `"--json" in output` is false. Asserting on that output tests the
    renderer's styling, not this command.
    """
    result = runner.invoke(app, ["list", "coverage", "--help"])
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# quickstart
# ---------------------------------------------------------------------------


def test_quickstart_runs_with_no_arguments(tmp_path: Path) -> None:
    """The headline promise: one command, no flags, no API key, a real score."""
    result = runner.invoke(app, ["quickstart", "--output", str(tmp_path / "runs")])
    assert result.exit_code == 0, result.output
    assert "Aggregate score:" in result.output
    assert "direct_qa" in result.output

    run_dirs = list((tmp_path / "runs").iterdir())
    assert len(run_dirs) == 1, "quickstart should produce exactly one run directory"
    assert (run_dirs[0] / "MANIFEST.json").is_file()


def test_quickstart_honours_an_explicit_task(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["quickstart", "--task", "JOB_SYS_001", "--output", str(tmp_path / "runs")]
    )
    assert result.exit_code == 0, result.output
    assert "JOB_SYS_001" in result.output


def test_quickstart_suggests_alternatives_for_a_mistyped_task(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["quickstart", "--task", "JOB_USR_01", "--output", str(tmp_path / "runs")]
    )
    assert result.exit_code == 2, result.output
    assert "JOB_USR_001" in result.output


# ---------------------------------------------------------------------------
# friendly errors on the main run path
# ---------------------------------------------------------------------------


def test_run_task_suggests_alternatives_for_a_mistyped_task(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "task", "--task", "JOB_USR_01", "--env", "env_01", "--output", str(tmp_path)],
    )
    assert result.exit_code == 2, result.output
    assert "Unknown task ID" in result.output
    assert "JOB_USR_001" in result.output
    assert "Traceback" not in result.output


def test_run_task_suggests_alternatives_for_a_mistyped_env(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "task", "--task", "JOB_USR_001", "--env", "env_99", "--output", str(tmp_path)],
    )
    assert result.exit_code == 2, result.output
    assert "Unknown environment ID" in result.output
    assert "Traceback" not in result.output


def test_run_task_resolves_the_corpus_from_outside_a_checkout(tmp_path: Path) -> None:
    """The exact command the README quick start prints, run from a wheel-like CWD."""
    result = runner.invoke(
        app,
        [
            "run", "task",
            "--task", "JOB_USR_001",
            "--env", "env_01",
            "--adapter", "direct_qa",
            "--output", str(tmp_path / "runs"),
            "--no-report",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "aggregate_score=" in result.output


def test_validate_benchmark_resolves_the_corpus_from_outside_a_checkout() -> None:
    result = runner.invoke(app, ["validate", "benchmark"])
    assert result.exit_code == 0, result.output
    assert "Validation passed." in result.output
