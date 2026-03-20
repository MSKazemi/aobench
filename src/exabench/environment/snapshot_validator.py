"""Validate HPC snapshot bundle artifacts against canonical Pydantic schemas."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from exabench.schemas.snapshot import IncidentMetadata, SlurmState


_TELEMETRY_REQUIRED_COLUMNS = {"timestamp", "node_id", "metric_name", "value", "unit"}


def validate_bundle(bundle_root: str | Path) -> list[str]:
    """Validate all structured files in a snapshot bundle.

    Returns a list of error strings. Empty list means the bundle is valid.
    """
    root = Path(bundle_root)
    errors: list[str] = []

    # slurm_state.json
    slurm_path = root / "slurm" / "slurm_state.json"
    if slurm_path.exists():
        try:
            SlurmState.model_validate(json.loads(slurm_path.read_text()))
        except Exception as e:
            errors.append(f"slurm/slurm_state.json: {e}")

    # incident_metadata.json
    inc_path = root / "incidents" / "incident_metadata.json"
    if inc_path.exists():
        try:
            IncidentMetadata.model_validate(json.loads(inc_path.read_text()))
        except Exception as e:
            errors.append(f"incidents/incident_metadata.json: {e}")

    # rbac_policy.yaml — check it is valid YAML with a 'roles' key
    rbac_path = root / "policy" / "rbac_policy.yaml"
    if rbac_path.exists():
        try:
            policy = yaml.safe_load(rbac_path.read_text())
            if not isinstance(policy, dict):
                errors.append("policy/rbac_policy.yaml: top-level must be a mapping")
            elif "roles" not in policy:
                errors.append("policy/rbac_policy.yaml: missing required key 'roles'")
        except Exception as e:
            errors.append(f"policy/rbac_policy.yaml: {e}")

    # telemetry_timeseries.parquet — check schema columns
    parquet_path = root / "telemetry" / "telemetry_timeseries.parquet"
    if parquet_path.exists():
        try:
            import pandas as pd

            df = pd.read_parquet(parquet_path)
            missing_cols = _TELEMETRY_REQUIRED_COLUMNS - set(df.columns)
            if missing_cols:
                errors.append(
                    f"telemetry/telemetry_timeseries.parquet: missing columns {sorted(missing_cols)}"
                )
        except Exception as e:
            errors.append(f"telemetry/telemetry_timeseries.parquet: {e}")

    return errors
