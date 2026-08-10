"""Execute every script in ``examples/`` so a broken example fails the build.

Documentation examples rot silently: an API changes, nobody re-runs the snippet, and a
new user's first experience is a traceback. These tests are cheap insurance — all four
examples run offline against the tool-free baseline, so the whole module costs a few
seconds and no API calls.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"

#: Examples that run standalone with no arguments.
STANDALONE = [
    "01_hello_aobench.py",
    "02_score_a_trace.py",
    "03_custom_adapter.py",
    "05_compare_two_adapters.py",
]


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


@pytest.mark.parametrize("script", STANDALONE)
def test_example_runs(script: str, tmp_path: Path) -> None:
    """Each standalone example exits 0 and prints a score."""
    result = _run([str(EXAMPLES_DIR / script)], cwd=REPO_ROOT)
    assert result.returncode == 0, (
        f"examples/{script} failed with exit {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert "score" in result.stdout.lower(), (
        f"examples/{script} produced no score in its output:\n{result.stdout}"
    )


def test_ci_gate_example_passes_and_fails(tmp_path: Path) -> None:
    """The CI gate example passes under a low threshold and fails under a high one."""
    run_dir = tmp_path / "run_example"
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True)
    (results_dir / "TASK_001_result.json").write_text(
        '{"task_id": "TASK_001", "aggregate_score": 0.75, "hard_fail": false}'
    )

    gate = str(EXAMPLES_DIR / "04_ci_gate.py")

    passing = _run([gate, str(run_dir), "--min-score", "0.50"], cwd=REPO_ROOT)
    assert passing.returncode == 0, passing.stdout + passing.stderr
    assert "PASS" in passing.stdout

    failing = _run([gate, str(run_dir), "--min-score", "0.90"], cwd=REPO_ROOT)
    assert failing.returncode == 1
    assert "FAIL" in failing.stdout


def test_ci_gate_example_fails_on_hard_fail(tmp_path: Path) -> None:
    """A hard fail fails the gate even when the score clears the threshold.

    This is the behaviour the gate exists for: an RBAC violation is a different class
    of event from a slightly-worse score, and must not be averaged away.
    """
    run_dir = tmp_path / "run_hardfail"
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True)
    (results_dir / "TASK_001_result.json").write_text(
        '{"task_id": "TASK_001", "aggregate_score": 0.99, "hard_fail": true}'
    )

    result = _run(
        [str(EXAMPLES_DIR / "04_ci_gate.py"), str(run_dir), "--min-score", "0.10"],
        cwd=REPO_ROOT,
    )
    assert result.returncode == 1, result.stdout
    assert "hard-fail" in result.stdout


def test_examples_readme_lists_every_script() -> None:
    """The examples README must mention every script in the directory."""
    readme = (EXAMPLES_DIR / "README.md").read_text()
    scripts = sorted(p.name for p in EXAMPLES_DIR.glob("*.py"))
    missing = [name for name in scripts if name not in readme]
    assert not missing, f"examples/README.md does not mention: {missing}"
