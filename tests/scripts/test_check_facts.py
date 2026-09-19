"""Regression coverage for the documented test-count gate in ``check_facts.py``."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"


def _import_script(name: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_documented_test_counts_fail_on_clear_drift() -> None:
    check_facts = _import_script("check_facts")
    failures = check_facts.documented_test_count_failures(
        actual_test_files=90,
        actual_tests=1584,
        docs={
            "README.md": "tests/                  # 83 test files, ~1510 tests (unit + integration)\n",
            "CONTRIBUTING.md": "make test           # ~1510 tests should pass\n",
        },
    )

    assert failures == [
        "README.md:1: documents 83 test files, but the tree has 90",
        "README.md:1: documents ~1510 tests, but pytest currently collects 1584 (allowed range 1520-1648)",
        "CONTRIBUTING.md:1: documents ~1510 tests, but pytest currently collects 1584 (allowed range 1520-1648)",
    ]


def test_documented_test_counts_allow_small_growth() -> None:
    check_facts = _import_script("check_facts")
    failures = check_facts.documented_test_count_failures(
        actual_test_files=90,
        actual_tests=1600,
        docs={
            "README.md": "tests/                  # 90 test files, ~1584 tests (unit + integration)\n",
            "CONTRIBUTING.md": "make test           # ~1584 tests should pass\n",
        },
    )

    assert failures == []
