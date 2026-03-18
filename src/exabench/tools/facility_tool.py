"""Mock facility tool — reads power, rack, and inventory data from environment bundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exabench.tools.base import BaseTool, ToolResult


class MockFacilityTool(BaseTool):
    """Exposes power, rack telemetry, and inventory data for facility_admin tasks.

    Reads CSV files from the environment bundle:
      power/   — node_power_*.csv, cluster_energy_*.csv, rack_energy_*.csv
      rack/    — rack_telemetry_*.csv
      inventory/ — node_map.csv, rack_mapping.csv, rack_layout.csv
    """

    name = "facility"

    def __init__(self, env_root: str, role: str) -> None:
        super().__init__(env_root)
        self._role = role

    def call(self, method: str, **kwargs: Any) -> ToolResult:
        dispatch = {
            "query_node_power": self._query_node_power,
            "query_cluster_energy": self._query_cluster_energy,
            "query_rack_telemetry": self._query_rack_telemetry,
            "list_inventory": self._list_inventory,
        }
        if method not in dispatch:
            return self._error(f"Unknown facility method: '{method}'")
        return dispatch[method](**kwargs)

    # ── Power ──────────────────────────────────────────────────────────────────

    def _query_node_power(self, node: str | None = None) -> ToolResult:
        """Return per-node power readings. Optionally filter by node name."""
        try:
            import pandas as pd
        except ImportError:
            return self._error("pandas is required for facility queries")

        power_dir = Path(self._env_root) / "power"
        if not power_dir.exists():
            return self._error("No power data directory in this environment")

        files = sorted(power_dir.glob("node_power_*.csv"))
        if not files:
            return self._error("No node_power CSV files found in power/")

        import pandas as pd  # noqa: F811 — re-import after try/except guard above
        df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
        if node:
            df = df[df["node"].astype(str) == str(node)]
        return self._ok(df.to_dict(orient="records"))

    def _query_cluster_energy(self) -> ToolResult:
        """Return cluster-level energy time series."""
        try:
            import pandas as pd
        except ImportError:
            return self._error("pandas is required for facility queries")

        power_dir = Path(self._env_root) / "power"
        if not power_dir.exists():
            return self._error("No power data directory in this environment")

        # Try rack_energy_*.csv first (env_04), then cluster_energy_*.csv (env_03)
        files = sorted(power_dir.glob("cluster_energy_*.csv")) or sorted(
            power_dir.glob("rack_energy_*.csv")
        )
        if not files:
            return self._error("No cluster/rack energy CSV files found in power/")

        import pandas as pd  # noqa: F811
        df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
        return self._ok(df.to_dict(orient="records"))

    # ── Rack ───────────────────────────────────────────────────────────────────

    def _query_rack_telemetry(self, rack_id: str | None = None) -> ToolResult:
        """Return rack telemetry (temperature, humidity, cooling status)."""
        try:
            import pandas as pd
        except ImportError:
            return self._error("pandas is required for facility queries")

        rack_dir = Path(self._env_root) / "rack"
        if not rack_dir.exists():
            return self._error("No rack data directory in this environment")

        files = sorted(rack_dir.glob("rack_telemetry_*.csv"))
        if not files:
            return self._error("No rack_telemetry CSV files found in rack/")

        import pandas as pd  # noqa: F811
        df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
        if rack_id:
            df = df[df["rack_id"].astype(str) == str(rack_id)]
        return self._ok(df.to_dict(orient="records"))

    # ── Inventory ──────────────────────────────────────────────────────────────

    def _list_inventory(self, kind: str = "nodes") -> ToolResult:
        """List inventory records. kind='nodes' (default) or 'racks'."""
        try:
            import pandas as pd
        except ImportError:
            return self._error("pandas is required for facility queries")

        inv_dir = Path(self._env_root) / "inventory"
        if not inv_dir.exists():
            return self._error("No inventory data directory in this environment")

        if kind == "racks":
            candidates = ["rack_mapping.csv", "rack_layout.csv"]
        else:
            candidates = ["node_map.csv"]

        for name in candidates:
            p = inv_dir / name
            if p.exists():
                import pandas as pd  # noqa: F811
                df = pd.read_csv(p)
                return self._ok(df.to_dict(orient="records"))

        return self._error(f"No inventory CSV found for kind='{kind}' in inventory/")
