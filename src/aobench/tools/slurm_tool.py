"""Mock SLURM tool — reads deterministic scheduler state from environment bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Literal, overload

from aobench.tools.base import BaseTool, ToolResult


class MockSlurmTool(BaseTool):
    name = "slurm"

    def __init__(self, env_root: str, role: str, requester_user: str = "alice") -> None:
        super().__init__(env_root)
        self._role = role
        self._requester_user = requester_user
        self._state = self._load_json("slurm/slurm_state.json")
        self._job_details = self._load_json("slurm/job_details.json")

    @overload
    def _load_json(self, rel_path: Literal["slurm/slurm_state.json"]) -> dict[str, Any]: ...

    @overload
    def _load_json(self, rel_path: str) -> dict[str, Any] | list[dict[str, Any]]: ...

    def _load_json(self, rel_path: str) -> dict[str, Any] | list[dict[str, Any]]:
        # State snapshots are mappings; job details may contain multiple records.
        p = Path(self._env_root) / rel_path
        if not p.exists():
            return {}
        with p.open(encoding="utf-8") as f:
            data: dict[str, Any] | list[dict[str, Any]] = json.load(f)
            return data

    def call(self, method: str, **kwargs: Any) -> ToolResult:
        dispatch: dict[str, Callable[..., ToolResult]] = {
            "query_jobs": self._query_jobs,
            "job_details": self._job_details_method,
            "list_nodes": self._list_nodes,
            "list_partitions": self._list_partitions,
        }
        if method not in dispatch:
            return self._error(f"Unknown SLURM method: '{method}'")
        return dispatch[method](**kwargs)

    def _query_jobs(self, user: str | None = None, state: str | None = None) -> ToolResult:
        jobs = self._state.get("jobs", [])
        # scientific_user can only see their own jobs
        if self._role == "scientific_user":
            jobs = [j for j in jobs if j.get("user") == self._requester_user]
        if user:
            jobs = [j for j in jobs if j.get("user") == user]
        if state:
            jobs = [j for j in jobs if j.get("state") == state.upper()]
        return self._ok(jobs)

    def _job_details_method(self, job_id: str) -> ToolResult:
        if not self._job_details:
            return self._error(f"No details found for job {job_id}")
        # job_details.json may be a single dict or a list of dicts
        if isinstance(self._job_details, list):
            record = next(
                (j for j in self._job_details if str(j.get("job_id", "")) == str(job_id)),
                None,
            )
            if record is None:
                return self._error(f"Job {job_id} not found")
        else:
            stored_id = str(self._job_details.get("job_id", ""))
            if stored_id != str(job_id):
                return self._error(f"Job {job_id} not found")
            record = self._job_details
        # scientific_user: only allowed to see their own job
        if self._role == "scientific_user":
            owner = record.get("sacct_record", {}).get("User")
            if owner != self._requester_user:
                return self._permission_denied(
                    f"Job {job_id} belongs to another user",
                    metadata={"cross_user": True, "job_owner": owner},
                )
        return self._ok(record)

    def _list_nodes(self) -> ToolResult:
        if self._role == "scientific_user":
            return self._permission_denied("scientific_user may not list nodes")
        return self._ok(self._state.get("nodes", []))

    def _list_partitions(self) -> ToolResult:
        return self._ok(self._state.get("partitions", []))
