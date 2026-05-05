"""T3 checker: Oracle solvability (deterministic path).

Verifies that a task is solvable by executing its ``derivation_query``
against the snapshot data and confirming a non-empty result is returned.

For tasks without a ``derivation_query``, the checker falls back to
verifying that the snapshot directory contains the data type directory
implied by the task's ``data_type`` field.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aobench.cli.validators.base import CheckResult

if TYPE_CHECKING:
    from aobench.schemas.task import HPCTaskSpec

# Mapping from HPCDataType to snapshot subdirectory
_DATA_TYPE_DIRS: dict[str, list[str]] = {
    "job_ops": ["slurm"],
    "node_ops": ["slurm", "telemetry"],
    "telemetry": ["telemetry"],
    "energy": ["telemetry"],
    "dataflow": ["slurm", "telemetry"],
    "rbac": ["policy"],
}


def check_oracle_solvability(
    task: "HPCTaskSpec",
    snapshot_dir: str | Path,
) -> CheckResult:
    """Check that the task can be solved from snapshot data.

    For tasks with ``ground_truth.derivation_query``, executes the query
    against JSON snapshot files.  For others, checks that the relevant
    data directories exist and are non-empty.

    Parameters
    ----------
    task:
        The HPC task spec to validate.
    snapshot_dir:
        Root environments directory.

    Returns
    -------
    CheckResult
        PASS — derivation query returns a result, or snapshot dirs present.
        FAIL — derivation query returns no result, or required dirs missing.
        SKIP — rubric-scored tasks (non-deterministic) or snapshot missing.
    """
    snapshot_dir = Path(snapshot_dir)
    env_path = snapshot_dir / task.snapshot_id

    if not env_path.exists():
        return CheckResult(
            status="SKIP",
            detail=f"Snapshot '{task.snapshot_id}' not found at '{env_path}'.",
            fix_suggestion=f"Generate snapshot bundle '{task.snapshot_id}'.",
        )

    # Rubric-mode tasks are not deterministically solvable — skip
    if task.scoring_mode == "rubric":
        return CheckResult(
            status="SKIP",
            detail=(
                f"Task '{task.task_id}' uses rubric scoring; oracle solvability "
                "check is not applicable for non-deterministic tasks."
            ),
        )

    # If a derivation query is present, try to execute it
    derivation_query: str | None = None
    if task.ground_truth is not None:
        derivation_query = task.ground_truth.derivation_query

    if derivation_query:
        return _run_derivation_query(task, derivation_query, env_path)

    # Fallback: check that required data dirs exist and have files
    return _check_data_dirs(task, env_path)


def _run_derivation_query(
    task: "HPCTaskSpec",
    query: str,
    env_path: Path,
) -> CheckResult:
    """Execute a derivation query string against snapshot JSON data.

    The query format is ``<subdir>/<filename>.json[<json_path>]``, e.g.:
    ``slurm/jobs.json[.[] | select(.job_id == 987654)]``

    For simple key lookups we support a lightweight path resolver.
    """
    try:
        result = _eval_query(query, env_path)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            status="FAIL",
            detail=f"Derivation query execution failed: {exc}",
            fix_suggestion=(
                "Check that the derivation_query path and syntax are correct, and "
                "that the referenced snapshot files exist and are valid JSON."
            ),
        )

    if result is None or result == [] or result == {}:
        return CheckResult(
            status="FAIL",
            detail=(
                f"Derivation query returned empty/null result for task '{task.task_id}'. "
                f"Query: '{query}'"
            ),
            fix_suggestion=(
                "Verify the derivation_query matches data in the snapshot, or update "
                "the ground_truth to reflect the actual snapshot state."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=(
            f"Derivation query returned a non-empty result for task '{task.task_id}'."
        ),
    )


def _eval_query(query: str, env_path: Path) -> Any:
    """Lightweight query evaluator for snapshot JSON files.

    Supports patterns:
    - ``subdir/file.json``                 → load and return entire file
    - ``subdir/file.json:key``             → return data[key]
    - ``subdir/file.json:key1.key2``       → nested key lookup
    """
    # Strip leading/trailing whitespace
    query = query.strip()

    # Split on colon to separate path from key path
    if ":" in query:
        file_part, key_path = query.split(":", 1)
    else:
        file_part = query
        key_path = ""

    json_file = env_path / file_part.strip()

    if not json_file.exists():
        raise FileNotFoundError(f"Snapshot file not found: '{json_file}'")

    data = json.loads(json_file.read_text(encoding="utf-8"))

    if not key_path:
        return data

    # Navigate nested keys
    parts = key_path.strip().split(".")
    current = data
    for part in parts:
        if not part:
            continue
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list):
            # Try to find first item matching part as a key
            matches = [item for item in current if isinstance(item, dict) and part in item]
            if not matches:
                return None
            current = [item[part] for item in matches]
        else:
            return None

    return current


def _check_data_dirs(task: "HPCTaskSpec", env_path: Path) -> CheckResult:
    """Fall back: verify required data directories exist and have content."""
    expected_dirs = _DATA_TYPE_DIRS.get(task.data_type, [])

    if not expected_dirs:
        return CheckResult(
            status="WARN",
            detail=(
                f"No known data directories for data_type='{task.data_type}'; "
                "cannot verify oracle solvability without derivation_query."
            ),
            fix_suggestion=(
                "Add a 'derivation_query' field to ground_truth to enable "
                "automated oracle solvability verification."
            ),
        )

    missing_dirs: list[str] = []
    empty_dirs: list[str] = []

    for subdir in expected_dirs:
        full_path = env_path / subdir
        if not full_path.exists():
            missing_dirs.append(subdir)
        elif not any(full_path.iterdir()):
            empty_dirs.append(subdir)

    if missing_dirs:
        return CheckResult(
            status="FAIL",
            detail=(
                f"Required data dir(s) missing for data_type='{task.data_type}': "
                f"{missing_dirs} in snapshot '{task.snapshot_id}'."
            ),
            fix_suggestion=(
                f"Create the following directories under '{env_path}': {missing_dirs}."
            ),
        )

    if empty_dirs:
        return CheckResult(
            status="WARN",
            detail=(
                f"Required data dir(s) exist but are empty: {empty_dirs} "
                f"in snapshot '{task.snapshot_id}'."
            ),
            fix_suggestion=(
                "Populate the empty directories with snapshot data files, or add a "
                "derivation_query to ground_truth for a stronger solvability check."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=(
            f"Required data directories for data_type='{task.data_type}' are present "
            f"and non-empty in snapshot '{task.snapshot_id}'."
        ),
    )
