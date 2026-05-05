"""Environment schema — HPC state snapshot metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

ImplementationStatus = Literal["planned", "scaffolded", "bundled", "validated"]
ValidationStatus = Literal["not_checked", "in_review", "validated", "failed"]


class EnvironmentMetadata(BaseModel):
    """Metadata for a deterministic HPC environment snapshot bundle."""

    environment_id: str
    snapshot_name: str
    scenario_type: str
    cluster_name: str
    snapshot_timestamp: datetime
    bundle_root: str
    supported_roles: list[str]
    supported_categories: list[str]
    included_sources: list[str]
    included_files: list[str]
    implementation_status: ImplementationStatus
    validation_status: ValidationStatus
    description: str


class EnvironmentBundle(BaseModel):
    """Loaded environment bundle: metadata + resolved filesystem root path."""

    metadata: EnvironmentMetadata
    root_path: str  # Absolute path to the environment directory on disk
