"""MANIFEST.json schema and writer for AOBench reproducibility pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class ManifestRecord(BaseModel):
    """Canonical MANIFEST.json record for one benchmark run.

    Written to data/runs/<run-id>/MANIFEST.json at the end of a run.
    Encodes every parameter needed to reproduce results verbatim.
    """

    run_id: str
    dataset_version: str
    # Semantic version of the benchmark dataset, e.g. "v0.2.0".

    engine_version: str
    # aobench package version string, e.g. "0.2.0".

    judge_config_id: Optional[str] = None
    # 16-hex-char sha-256 prefix identifying judge model + prompts + params.
    # None when judge scoring was not applied.

    snapshot_bundle_sha256: Optional[str] = None
    # SHA-256 of the canonical snapshot bundle tarball.
    # None when bundles are loaded from disk without integrity verification.

    agent_model: str
    # Model identifier used for the agent, e.g. "gpt-4o-2024-11-20".

    agent_seed: Optional[int] = None
    # Random seed passed to the agent adapter. None for non-deterministic runs.

    split: str
    # Dataset split used: "dev" | "public_test" | "hidden_test".

    task_ids: list[str]
    # Ordered list of task IDs included in this run.

    python_version: str
    # Python version string, e.g. "3.11.9".

    os_name: str
    # Operating system name, e.g. "Linux-6.1.0-x86_64".

    gpu_info: Optional[str] = None
    # GPU identifier string, e.g. "NVIDIA A100 80GB". None for CPU-only runs.

    validity_gates: dict[str, bool] = {}
    # Map of gate_name → pass/fail for V1–V6 validity gates.

    created_at: str
    # ISO-8601 UTC timestamp of manifest creation, e.g. "2026-05-01T12:00:00Z".


def write_manifest(record: ManifestRecord, output_dir: Path) -> Path:
    """Write MANIFEST.json into output_dir.

    Parameters
    ----------
    record:
        Populated ManifestRecord to serialise.
    output_dir:
        Directory where MANIFEST.json will be written. Created if absent.

    Returns
    -------
    Path
        Absolute path of the written file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "MANIFEST.json"
    path.write_text(
        json.dumps(record.model_dump(), indent=2, default=str),
        encoding="utf-8",
    )
    return path
