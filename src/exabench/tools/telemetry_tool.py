"""Mock telemetry tool — reads CSV/Parquet telemetry from environment bundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exabench.tools.base import BaseTool, ToolResult


class MockTelemetryTool(BaseTool):
    name = "telemetry"

    def __init__(self, env_root: str, role: str) -> None:
        super().__init__(env_root)
        self._role = role

    def call(self, method: str, **kwargs: Any) -> ToolResult:
        dispatch = {
            "query_memory_events": self._query_memory_events,
            "list_metrics": self._list_metrics,
        }
        if method not in dispatch:
            return self._error(f"Unknown telemetry method: '{method}'")
        return dispatch[method](**kwargs)

    def _query_memory_events(self, job_id: str | None = None) -> ToolResult:
        try:
            import pandas as pd
        except ImportError:
            return self._error("pandas is required for telemetry queries")

        csv_path = Path(self._env_root) / "telemetry" / "memory_events.csv"
        if not csv_path.exists():
            return self._error("memory_events.csv not found in this environment")

        df = pd.read_csv(csv_path)
        if job_id:
            if "job_id" in df.columns:
                df = df[df["job_id"].astype(str) == str(job_id)]
        return self._ok(df.to_dict(orient="records"))

    def _list_metrics(self) -> ToolResult:
        telemetry_dir = Path(self._env_root) / "telemetry"
        files = [p.name for p in telemetry_dir.iterdir()] if telemetry_dir.exists() else []
        return self._ok(files)
