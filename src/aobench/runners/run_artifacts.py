"""Emit MANIFEST.json and COMPUTE.json per run directory for P8 pre-flight gate."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aobench.utils.logging import get_logger

logger = get_logger(__name__)

# ── Internal helpers ──────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_output(*args: str) -> str:
    """Run a git sub-command and return stdout stripped; 'unknown' on any failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _sha256_file(path: Path) -> str | None:
    """Return hex SHA-256 of a file, or None if the file does not exist."""
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_judge_config_id(repo_root: Path | None = None) -> str | None:
    """Return the judge_config_id from data/judge_config.json, or None."""
    search_roots = []
    if repo_root is not None:
        search_roots.append(repo_root)
    # Try cwd as fallback
    search_roots.append(Path("."))
    for root in search_roots:
        p = root / "data" / "judge_config.json"
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("judge_config_id")
            except Exception:
                pass
    return None


def _snapshot_manifest_sha(repo_root: Path | None = None) -> str | None:
    """Return sha256 of data/snapshots/MANIFEST.json, or None."""
    search_roots = []
    if repo_root is not None:
        search_roots.append(repo_root)
    search_roots.append(Path("."))
    for root in search_roots:
        p = root / "data" / "snapshots" / "MANIFEST.json"
        sha = _sha256_file(p)
        if sha is not None:
            return sha
    return None


# ── Public API ────────────────────────────────────────────────────────────────


def write_run_manifest(
    run_dir: Path,
    *,
    model: str,
    adapter: str,
    split: str,
    judge_config_id: str | None = None,
    repo_root: Path | None = None,
) -> None:
    """Write skeleton MANIFEST.json at run start; fills git provenance.

    Parameters
    ----------
    run_dir:
        The per-run output directory (e.g. ``data/runs/<run-id>``).
        Created if absent.
    model:
        Model identifier used by the agent adapter.
    adapter:
        Adapter name (e.g. ``"direct_qa"``, ``"openai:gpt-4o"``).
    split:
        Dataset split used: ``"all" | "dev" | "lite" | "test"``.
    judge_config_id:
        Explicit judge config ID override. When ``None``, the function
        attempts to load it from ``data/judge_config.json``.
    repo_root:
        Root of the AOBench repo (used to locate ``data/``).  Falls back
        to the current working directory when ``None``.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    if judge_config_id is None:
        judge_config_id = _load_judge_config_id(repo_root)

    record: dict[str, Any] = {
        "dataset_version": "aobench-v0.2.0",
        "repo_tag": _git_output("describe", "--tags", "--always"),
        "commit_hash": _git_output("rev-parse", "HEAD"),
        "model": model,
        "adapter": adapter,
        "split": split,
        "judge_config_id": judge_config_id,
        "snapshot_manifest_sha": _snapshot_manifest_sha(repo_root),
        "python_version": sys.version,
        "os_name": platform.platform(),
        "started_at": _now_iso(),
        "finished_at": None,
    }

    path = run_dir / "MANIFEST.json"
    path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    logger.debug("MANIFEST.json written  run_dir=%s", run_dir)


def finalize_run_artifacts(run_dir: Path, results: list) -> None:
    """Write final MANIFEST.json (adds finished_at) and COMPUTE.json.

    Parameters
    ----------
    run_dir:
        The per-run output directory where ``MANIFEST.json`` was previously
        written by :func:`write_run_manifest`.
    results:
        List of :class:`~aobench.schemas.result.BenchmarkResult` objects (or
        ``None`` for failed tasks).  Each item may be a bare result or a
        ``(task_id, result)`` tuple — both forms are handled.  Missing
        ``cost_estimate_usd`` / ``latency_seconds`` fields default to 0.
    """
    run_dir = Path(run_dir)

    # ── Normalise results list ─────────────────────────────────────────────────
    # Accept either [result, ...] or [(task_id, result), ...] without caring
    # which form the caller used.
    normalised: list[Any] = []
    for item in results:
        if isinstance(item, tuple) and len(item) == 2:
            normalised.append(item[1])
        else:
            normalised.append(item)

    valid_results = [r for r in normalised if r is not None]

    # ── Aggregate compute metrics ──────────────────────────────────────────────
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_usd: float = 0.0
    total_wall_s: float = 0.0
    task_count: int = len(normalised)  # includes failed tasks in denominator

    for r in valid_results:
        total_tokens_in += getattr(r, "prompt_tokens", None) or 0
        total_tokens_out += getattr(r, "completion_tokens", None) or 0
        total_usd += getattr(r, "cost_estimate_usd", None) or 0.0
        total_wall_s += getattr(r, "latency_seconds", None) or 0.0

    denom = task_count if task_count > 0 else 1

    compute: dict[str, Any] = {
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "total_usd": total_usd,
        "total_wall_s": total_wall_s,
        "task_count": task_count,
        "per_task_avg_usd": total_usd / denom,
        "per_task_avg_wall_s": total_wall_s / denom,
    }

    compute_path = run_dir / "COMPUTE.json"
    compute_path.write_text(json.dumps(compute, indent=2), encoding="utf-8")
    logger.debug("COMPUTE.json written  run_dir=%s", run_dir)

    # ── Finalise MANIFEST.json ─────────────────────────────────────────────────
    manifest_path = run_dir / "MANIFEST.json"
    try:
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            logger.warning("MANIFEST.json not found in %s — creating minimal record", run_dir)
            data = {}
        data["finished_at"] = _now_iso()
        manifest_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.debug("MANIFEST.json finalised  run_dir=%s", run_dir)
    except Exception:
        logger.exception("Failed to finalise MANIFEST.json in %s", run_dir)
