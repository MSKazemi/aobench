"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Bypass the V0 fidelity gate in all tests: test fixtures are small synthetic
# snapshots that intentionally do not match real HPC distributions.
os.environ.setdefault("EXABENCH_SKIP_FIDELITY", "1")

TESTS_DIR = Path(__file__).parent
BENCHMARK_DIR = TESTS_DIR.parent / "benchmark"
TEST_DATA_DIR = TESTS_DIR / "data"


@pytest.fixture
def benchmark_root() -> Path:
    return BENCHMARK_DIR


@pytest.fixture
def test_env_dir() -> Path:
    return TEST_DATA_DIR / "environments" / "test_env_01"


@pytest.fixture
def test_task_path() -> Path:
    return TEST_DATA_DIR / "tasks" / "test_task_001.json"
