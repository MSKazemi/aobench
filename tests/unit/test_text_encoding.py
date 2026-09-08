"""Regression cover for encoding-less text I/O (reported via issue #60).

A run on Windows died at task 6 of 67 with a ``UnicodeEncodeError``, because
``TraceWriter`` wrote agent output containing an emoji through a ``write_text``
call with no ``encoding=``. On Windows that resolves to cp1252.
"""

from __future__ import annotations

from pathlib import Path

from aobench.runners.trace_writer import TraceWriter
from aobench.schemas.trace import Trace
from scripts.check_text_encoding import find_violations

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "src" / "aobench"

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
    """Static gate: the whole package, not just the one call that was reported."""
    violations = find_violations(SRC)
    assert violations == [], (
        "text I/O without encoding= breaks on Windows (cp1252):\n"
        + "\n".join(f"  {rel}:{line}: {name}()" for rel, line, name in violations)
    )
