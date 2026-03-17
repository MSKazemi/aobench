"""ID generation utilities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def _ts() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


def _short_uuid() -> str:
    return uuid.uuid4().hex[:8]


def make_run_id() -> str:
    return f"run_{_ts()}_{_short_uuid()}"


def make_trace_id() -> str:
    return f"trace_{_ts()}_{_short_uuid()}"


def make_result_id() -> str:
    return f"result_{_ts()}_{_short_uuid()}"
