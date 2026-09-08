"""Regression cover for encoding-less text I/O (reported via issue #60).

A run on Windows died at task 6 of 67 with a ``UnicodeEncodeError``, because
``TraceWriter`` wrote agent output containing an emoji through a ``write_text``
call with no ``encoding=``. On Windows that resolves to cp1252.
"""

from __future__ import annotations

from pathlib import Path

from aobench.runners.trace_writer import TraceWriter
from aobench.schemas.trace import Trace
from scripts.check_text_encoding import SCANNED, find_violations

ROOT = Path(__file__).resolve().parent.parent.parent

# Emoji, an em-dash, and non-Latin script — all unencodable in cp1252.
NON_ASCII = "job finished ✅ — узел node-042 是正常的"


def test_trace_writer_round_trips_non_ascii(tmp_path):
    trace = Trace(
        trace_id="t1",
        run_id="r1",
        task_id="JOB_USR_001",
        role="scientific_user",
        environment_id="env_01",
        adapter_name="direct_qa",
        final_answer=NON_ASCII,
    )
    out = TraceWriter(tmp_path).write_trace(trace)
    reloaded = Trace.model_validate_json(out.read_text(encoding="utf-8"))
    assert reloaded.final_answer == NON_ASCII


def test_no_text_io_omits_an_encoding():
    """Static gate over src, tests and scripts — not just the reported call.

    ``tests/`` counts: a contributor who cannot run the suite on Windows is as
    blocked as one whose benchmark run dies partway through.
    """
    violations: list[tuple[str, int, str]] = []
    for tree in SCANNED:
        violations.extend(find_violations(ROOT / tree))
    assert violations == [], (
        "text I/O without encoding= breaks on Windows (cp1252):\n"
        + "\n".join(f"  {rel}:{line}: {name}()" for rel, line, name in violations)
    )
