"""Mock telemetry tool — reads CSV/Parquet telemetry from environment bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exabench.tools.base import BaseTool, ToolResult

# Roles that may access any node's telemetry (not restricted to own-job nodes).
_FULL_ACCESS_ROLES = {"sysadmin", "facility_admin", "system_designer"}


class MockTelemetryTool(BaseTool):
    name = "telemetry"

    def __init__(self, env_root: str, role: str) -> None:
        super().__init__(env_root)
        self._role = role

    def call(self, method: str, **kwargs: Any) -> ToolResult:
        dispatch = {
            "query_memory_events": self._query_memory_events,
            "list_metrics": self._list_metrics,
            "query_timeseries": self._query_timeseries,
            "query_node_metrics": self._query_node_metrics,
        }
        if method not in dispatch:
            return self._error(f"Unknown telemetry method: '{method}'")
        return dispatch[method](**kwargs)

    # ── Existing methods ───────────────────────────────────────────────────────

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

    # ── New parquet-backed methods ─────────────────────────────────────────────

    def _query_timeseries(
        self,
        node_id: str | None = None,
        metric_name: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> ToolResult:
        """Query the canonical telemetry time-series parquet with optional filters.

        Args:
            node_id: Filter to a specific node (e.g. "node01").
            metric_name: Filter to a specific metric (e.g. "cpu_util_pct").
            start: ISO8601 UTC lower bound (inclusive).
            end: ISO8601 UTC upper bound (inclusive).

        Role access:
            sysadmin / facility_admin / system_designer: full access.
            scientific_user / researcher: restricted to nodes that ran their own jobs.
        """
        try:
            import pandas as pd
        except ImportError:
            return self._error("pandas is required for telemetry queries")

        parquet_path = Path(self._env_root) / "telemetry" / "telemetry_timeseries.parquet"
        if not parquet_path.exists():
            return self._error("telemetry_timeseries.parquet not found in this environment")

        df = pd.read_parquet(parquet_path)

        # Role-based node filtering for restricted roles
        if self._role not in _FULL_ACCESS_ROLES:
            allowed_nodes = self._get_allowed_nodes()
            if allowed_nodes is not None:
                if node_id is not None and node_id not in allowed_nodes:
                    return self._permission_denied(
                        "Node not in own job allocation",
                        metadata={"node_not_in_own_jobs": True},
                    )
                df = df[df["node_id"].isin(allowed_nodes)]

        if node_id:
            df = df[df["node_id"] == node_id]
        if metric_name:
            df = df[df["metric_name"] == metric_name]
        if start:
            df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
        if end:
            df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

        return self._ok(df.to_dict(orient="records"))

    def _query_node_metrics(self, node_id: str) -> ToolResult:
        """Return a per-node summary (latest value for each metric) from parquet."""
        try:
            import pandas as pd
        except ImportError:
            return self._error("pandas is required for telemetry queries")

        parquet_path = Path(self._env_root) / "telemetry" / "telemetry_timeseries.parquet"
        if not parquet_path.exists():
            return self._error("telemetry_timeseries.parquet not found in this environment")

        df = pd.read_parquet(parquet_path)

        if self._role not in _FULL_ACCESS_ROLES:
            allowed_nodes = self._get_allowed_nodes()
            if allowed_nodes is not None and node_id not in allowed_nodes:
                return self._permission_denied(
                    f"Role '{self._role}' does not have access to node '{node_id}' telemetry"
                )

        node_df = df[df["node_id"] == node_id]
        if node_df.empty:
            return self._error(f"No telemetry data found for node '{node_id}'")

        # Latest value per metric
        summary = (
            node_df.sort_values("timestamp")
            .groupby("metric_name")
            .last()[["value", "unit"]]
            .reset_index()
            .to_dict(orient="records")
        )
        return self._ok({"node_id": node_id, "metrics": summary})

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_allowed_nodes(self) -> set[str] | None:
        """Return the set of node names visible to a restricted role, or None for all."""
        slurm_path = Path(self._env_root) / "slurm" / "slurm_state.json"
        if not slurm_path.exists():
            return None
        try:
            state = json.loads(slurm_path.read_text())
        except Exception:
            return None

        # For now, restricted roles can see all nodes in the snapshot.
        # In a richer implementation this would cross-ref jobs by requester_user.
        return {n["name"] for n in state.get("nodes", [])}
