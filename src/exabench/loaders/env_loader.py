"""Load and validate environment bundles from disk."""

from __future__ import annotations

from pathlib import Path

import yaml

from exabench.schemas.environment import EnvironmentBundle, EnvironmentMetadata


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

    return EnvironmentBundle(metadata=metadata, root_path=str(env_dir))
