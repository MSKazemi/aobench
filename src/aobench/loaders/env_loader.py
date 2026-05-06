"""Load and validate environment bundles from disk."""

from __future__ import annotations

from pathlib import Path

import yaml

from aobench.environment.snapshot_validator import validate_bundle
from aobench.schemas.environment import EnvironmentBundle, EnvironmentMetadata


def load_environment(env_dir: str | Path) -> EnvironmentBundle:
    """Load an environment bundle from its directory, validating metadata and manifest."""
    env_dir = Path(env_dir).resolve()
    if not env_dir.is_dir():
        raise NotADirectoryError(f"Environment directory not found: {env_dir}")

    metadata_path = env_dir / "metadata.yaml"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata.yaml in {env_dir}")

    with metadata_path.open() as f:
        raw = yaml.safe_load(f)

    metadata = EnvironmentMetadata.model_validate(raw)

    # Validate that declared files are present
    missing = [f for f in metadata.included_files if not (env_dir / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Environment {metadata.environment_id} is missing declared files: {missing}"
        )

    # Validate structured artifact schemas (slurm_state.json, incident_metadata.json, etc.)
    errors = validate_bundle(env_dir)
    if errors:
        raise ValueError(
            f"Bundle validation failed for {metadata.environment_id}:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    # V0 fidelity gate
    import os
    if os.environ.get("AOBENCH_SKIP_FIDELITY") != "1":
        from aobench.environment.fidelity_report import FidelityReport
        report = FidelityReport(env_id=metadata.environment_id, env_dir=env_dir)
        report.run_all()
        if not report.passed:
            failed = [r.validator_id for r in report.results if not r.passed]
            raise ValueError(
                f"Fidelity check failed for {metadata.environment_id}: "
                f"checks {failed} did not pass. "
                f"Run 'aobench validate fidelity' to see details. "
                f"Set AOBENCH_SKIP_FIDELITY=1 to bypass (development only)."
            )

    return EnvironmentBundle(metadata=metadata, root_path=str(env_dir))
