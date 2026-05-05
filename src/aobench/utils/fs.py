"""Filesystem helpers."""

from __future__ import annotations

from pathlib import Path


def resolve_benchmark_root(given: str | Path | None = None) -> Path:
    """Find the benchmark/ directory relative to the package or given path."""
    if given:
        return Path(given).resolve()
    # Walk up from this file to find benchmark/
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "benchmark"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Could not locate benchmark/ directory")
