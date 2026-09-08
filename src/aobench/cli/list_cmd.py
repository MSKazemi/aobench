"""``aobench list`` — discover what is inside the benchmark without reading JSON.

Every other sub-command takes a `--task` or `--env` ID. Before this command existed
the only way to learn a valid ID was to `ls benchmark/tasks/specs/`, which is a poor
first experience and impossible from an installed wheel. Each sub-command here is a
read-only view over the corpus resolved by :func:`aobench.cli._common.resolve_root`.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import typer
import yaml

from aobench.cli._common import resolve_root

list_app = typer.Typer(
    help="List the tasks, environments, roles, QCATs, adapters, scorers, and profiles.",
    no_args_is_help=True,
)

# Kept here rather than imported from the adapter package so `aobench list adapters`
# never pays the import cost (or the ImportError) of an optional provider SDK.
_ADAPTERS: list[tuple[str, str, str]] = [
    ("direct_qa", "none", "Tool-free reference baseline. No API key, fully offline."),
    ("openai", "openai", "Any OpenAI-compatible chat model, e.g. `openai:gpt-4o`."),
    ("anthropic", "anthropic", "Anthropic models, e.g. `anthropic:claude-3-5-sonnet-20241022`."),
    ("mcp", "mcp", "Any MCP server, e.g. `mcp:stdio:python my_server.py`."),
]

_QCAT_DESCRIPTIONS: dict[str, str] = {
    "JOB": "Job submission, scheduling, and queue reasoning",
    "MON": "Monitoring and telemetry interpretation",
    "ENERGY": "Power and energy reasoning",
    "PERF": "Performance analysis and bottleneck attribution",
    "DATA": "Data movement, storage, and filesystem operations",
    "SEC": "Security posture and access questions",
    "FAC": "Facility and cooling operations",
    "ARCH": "Architecture and capability questions",
    "AIOPS": "Anomaly detection and incident response",
    "DOCS": "Documentation lookup and policy grounding",
}

_ROLE_DESCRIPTIONS: dict[str, str] = {
    "scientific_user": "Runs science on the cluster; no administrative rights",
    "sysadmin": "Operates the cluster; broad but audited tool access",
    "facility_admin": "Owns power, cooling, and the machine room",
    "researcher": "Studies the system itself; read-mostly analytical access",
    "system_designer": "Plans future systems; architecture and capacity questions",
}

# Role -> the short code already used in every non-M100 task_id, e.g. JOB_USR_004.
# Order matches the column order in issue #28's own example output (USR SYS RES FAC DES).
_ROLE_CODES: dict[str, str] = {
    "scientific_user": "USR",
    "sysadmin": "SYS",
    "researcher": "RES",
    "facility_admin": "FAC",
    "system_designer": "DES",
}

# Stand-in axis label for a spec whose qcat or role is missing or blank, so such a task
# is still counted somewhere visible instead of vanishing from the coverage matrix.
_UNSET = "(unset)"


def _is_m100_grounded(spec: dict[str, Any]) -> bool:
    """True when *spec* is a task grounded in real Marconi100 ExaData.

    The ``M100_`` task_id prefix is the corpus-wide convention for grounded tasks. Both
    ``list tasks --grounded`` and ``list coverage`` go through here so the two can never
    drift apart on what "grounded" means.
    """
    return str(spec.get("task_id", "")).startswith("M100_")


def _load_specs(root: Path) -> list[dict[str, Any]]:
    spec_dir = root / "tasks" / "specs"
    if not spec_dir.is_dir():
        typer.echo(f"No task specs found under {spec_dir}", err=True)
        raise typer.Exit(code=2)
    specs = []
    for path in sorted(spec_dir.glob("*.json")):
        try:
            specs.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            typer.echo(f"Skipping malformed spec {path.name}: {exc}", err=True)
    return specs


def _load_env_metadata(root: Path) -> list[dict[str, Any]]:
    env_root = root / "environments"
    if not env_root.is_dir():
        typer.echo(f"No environments found under {env_root}", err=True)
        raise typer.Exit(code=2)
    envs = []
    # Only `env_*` directories are environments; siblings such as `_m100_reference`
    # are shared source material, not runnable bundles.
    for path in sorted(p for p in env_root.iterdir() if p.is_dir() and p.name.startswith("env_")):
        meta_path = path / "metadata.yaml"
        meta: dict[str, Any] = {"environment_id": path.name}
        if meta_path.is_file():
            loaded = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                meta.update(loaded)
        envs.append(meta)
    return envs


def _emit(rows: list[dict[str, Any]], columns: list[str], as_json: bool) -> None:
    """Print ``rows`` either as machine-readable JSON or an aligned text table."""
    if as_json:
        typer.echo(json.dumps(rows, indent=2))
        return
    if not rows:
        typer.echo("(nothing matched)")
        return
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}
    typer.echo("  ".join(c.upper().ljust(widths[c]) for c in columns).rstrip())
    for row in rows:
        typer.echo("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in columns).rstrip())
    typer.echo(f"\n{len(rows)} row{'s' if len(rows) != 1 else ''}.")


@list_app.command("tasks")
def list_tasks(
    qcat: str = typer.Option(None, "--qcat", help="Filter by question category, e.g. JOB."),
    role: str = typer.Option(None, "--role", help="Filter by role, e.g. sysadmin."),
    split: str = typer.Option(None, "--split", help="Filter by benchmark split: dev or test."),
    env: str = typer.Option(None, "--env", help="Filter by the environment the task targets."),
    grounded: bool = typer.Option(
        False, "--grounded", help="Only tasks grounded in real Marconi100 ExaData."
    ),
    ids_only: bool = typer.Option(False, "--ids-only", help="Print bare task IDs, one per line."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root"),
) -> None:
    """List benchmark tasks, optionally filtered."""
    root = resolve_root(benchmark_root)
    specs = _load_specs(root)

    def keep(spec: dict[str, Any]) -> bool:
        if qcat and str(spec.get("qcat", "")).upper() != qcat.upper():
            return False
        if role and str(spec.get("role", "")) != role:
            return False
        if split and str(spec.get("benchmark_split", "")) != split:
            return False
        if env and str(spec.get("environment_id", "")) != env:
            return False
        return not (grounded and not _is_m100_grounded(spec))

    rows = [
        {
            "task_id": s.get("task_id", ""),
            "qcat": s.get("qcat", ""),
            "role": s.get("role", ""),
            "split": s.get("benchmark_split", ""),
            "env": s.get("environment_id", ""),
            "difficulty": s.get("difficulty_tier", s.get("difficulty", "")),
            "title": s.get("title", ""),
        }
        for s in specs
        if keep(s)
    ]

    if ids_only:
        for row in rows:
            typer.echo(row["task_id"])
        return
    _emit(rows, ["task_id", "qcat", "role", "split", "env", "difficulty", "title"], as_json)


@list_app.command("envs")
def list_envs(
    grounded: bool = typer.Option(
        False, "--grounded", help="Only environments built from real Marconi100 ExaData."
    ),
    role: str = typer.Option(None, "--role", help="Only environments supporting this role."),
    ids_only: bool = typer.Option(False, "--ids-only", help="Print bare environment IDs."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root"),
) -> None:
    """List environment snapshot bundles."""
    root = resolve_root(benchmark_root)
    envs = _load_env_metadata(root)

    def keep(meta: dict[str, Any]) -> bool:
        env_id = str(meta.get("environment_id", ""))
        if grounded and not env_id.startswith("env_m100_"):
            return False
        return not (role and role not in (meta.get("supported_roles") or []))

    rows = [
        {
            "env_id": m.get("environment_id", ""),
            "cluster": m.get("cluster_name", ""),
            "scenario": m.get("scenario_type", ""),
            "grounding": (
                "real-M100"
                if str(m.get("environment_id", "")).startswith("env_m100_")
                else "synthetic"
            ),
            "sources": ",".join(m.get("included_sources") or []),
            "name": m.get("snapshot_name", ""),
        }
        for m in envs
        if keep(m)
    ]

    if ids_only:
        for row in rows:
            typer.echo(row["env_id"])
        return
    _emit(rows, ["env_id", "cluster", "scenario", "grounding", "sources", "name"], as_json)


@list_app.command("qcats")
def list_qcats(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root"),
) -> None:
    """List the question categories (QCATs) with a task count each."""
    specs = _load_specs(resolve_root(benchmark_root))
    counts = Counter(str(s.get("qcat", "")) for s in specs)
    rows = [
        {
            "qcat": qcat,
            "tasks": count,
            "description": _QCAT_DESCRIPTIONS.get(qcat, ""),
        }
        for qcat, count in sorted(counts.items())
        if qcat
    ]
    _emit(rows, ["qcat", "tasks", "description"], as_json)


@list_app.command("roles")
def list_roles(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root"),
) -> None:
    """List the operator roles with a task count each."""
    specs = _load_specs(resolve_root(benchmark_root))
    counts = Counter(str(s.get("role", "")) for s in specs)
    rows = [
        {
            "role": role,
            "tasks": count,
            "description": _ROLE_DESCRIPTIONS.get(role, ""),
        }
        for role, count in sorted(counts.items())
        if role
    ]
    _emit(rows, ["role", "tasks", "description"], as_json)


@list_app.command("adapters")
def list_adapters(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List the agent adapters and the extra each one needs."""
    rows = [
        {"adapter": name, "extra": extra, "description": desc} for name, extra, desc in _ADAPTERS
    ]
    _emit(rows, ["adapter", "extra", "description"], as_json)


@list_app.command("profiles")
def list_profiles(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root"),
) -> None:
    """List the scoring weight profiles and their per-dimension weights."""
    root = resolve_root(benchmark_root)
    config = root / "configs" / "scoring_profiles.yaml"
    if not config.is_file():
        typer.echo(f"No scoring profiles at {config}", err=True)
        raise typer.Exit(code=2)
    profiles = (yaml.safe_load(config.read_text(encoding="utf-8")) or {}).get("profiles", {})

    rows = []
    for name, profile in sorted(profiles.items()):
        weights = profile.get("weights", {})
        row: dict[str, Any] = {"profile": name, "version": profile.get("version", "")}
        row.update({dim: f"{value:.2f}" for dim, value in weights.items()})
        rows.append(row)

    dims = sorted({d for r in rows for d in r if d not in {"profile", "version"}})
    _emit(rows, ["profile", "version", *dims], as_json)


@list_app.command("scorers")
def list_scorers(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List the scorers wired into the aggregate score, with their dimension."""
    from aobench.scorers.aggregate import AggregateScorer  # noqa: PLC0415

    rows = [
        {
            "dimension": scorer.dimension,
            "scorer": type(scorer).__name__,
            "description": (type(scorer).__doc__ or "").strip().splitlines()[0]
            if type(scorer).__doc__
            else "",
        }
        for scorer in AggregateScorer.scorers()
    ]
    _emit(rows, ["dimension", "scorer", "description"], as_json)


@list_app.command("coverage")
def list_coverage(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root"),
) -> None:
    """Show the QCAT x role task-count matrix, and call out the thin and empty cells."""
    # Counts come from each TaskSpec's own qcat/role fields, not from parsing task_id
    # strings: the M100_* tasks carry an extra "M100_" segment that shifts every position
    # after it, so a filename-parsing approach silently miscounts them.
    #
    # The axes are the *union* of the documented QCATs/roles and whatever the corpus
    # actually contains. A task carrying an unrecognised or blank qcat/role therefore
    # still lands in a visible row or column, rather than being dropped from a matrix
    # whose header claims to be the size of the corpus. Deciding whether such a value is
    # *legal* belongs to `aobench validate benchmark`; `list` only ever describes what is
    # actually there, exactly as `list qcats` and `list roles` already do.
    #
    # M100 tasks are otherwise ordinary tasks with real qcat/role metadata, so they are
    # included in the main matrix like any other task; the second table below breaks out
    # just the M100-grounded subset, so it stays visible how much of any cell's coverage
    # is grounded in real Marconi100 data versus synthetic. The two tables therefore
    # overlap by design -- the second is a subset of the first, not an addition to it.
    specs = _load_specs(resolve_root(benchmark_root))

    def _qcat_of(spec: dict[str, Any]) -> str:
        return str(spec.get("qcat") or "").strip() or _UNSET

    def _role_of(spec: dict[str, Any]) -> str:
        return str(spec.get("role") or "").strip() or _UNSET

    qcats = sorted(set(_QCAT_DESCRIPTIONS) | {_qcat_of(s) for s in specs})
    # Documented roles keep their documented order; anything else the corpus contains is
    # appended alphabetically so it is visible rather than silently uncounted.
    extra_roles = sorted({_role_of(s) for s in specs} - set(_ROLE_CODES))
    roles = [*_ROLE_CODES, *extra_roles]

    # Short column headers. Undocumented roles fall back to their own name; the loop
    # guarantees the headers stay distinct so two roles can never share a column.
    codes_by_role: dict[str, str] = {}
    for role in roles:
        code = _ROLE_CODES.get(role) or role.upper()
        while code in codes_by_role.values():
            code += "*"
        codes_by_role[role] = code
    codes = [codes_by_role[r] for r in roles]

    def _build_matrix(specs_in: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        matrix: dict[str, dict[str, int]] = {q: dict.fromkeys(roles, 0) for q in qcats}
        for spec in specs_in:
            matrix[_qcat_of(spec)][_role_of(spec)] += 1
        return matrix

    matrix = _build_matrix(specs)
    m100_matrix = _build_matrix([s for s in specs if _is_m100_grounded(s)])

    def _rows(m: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for q in qcats:
            row: dict[str, Any] = {"qcat": q}
            row.update({codes_by_role[r]: m[q][r] for r in roles})
            row["total"] = sum(m[q][r] for r in roles)
            out.append(row)
        return out

    main_rows = _rows(matrix)
    total_tasks = sum(r["total"] for r in main_rows)
    cells_total = len(qcats) * len(roles)
    # An empty cell is a coverage gap and a thin cell is a single point of failure; both
    # are reported, and empty cells are a subset of thin ones.
    thin_cells = sorted(
        f"{q}_{codes_by_role[r]}" for q in qcats for r in roles if matrix[q][r] <= 1
    )
    empty_cells = sorted(
        f"{q}_{codes_by_role[r]}" for q in qcats for r in roles if not matrix[q][r]
    )
    m100_rows = _rows(m100_matrix)
    m100_total = sum(r["total"] for r in m100_rows)

    if as_json:
        typer.echo(
            json.dumps(
                {
                    "qcat_role_counts": main_rows,
                    "total_tasks": total_tasks,
                    "cells_total": cells_total,
                    "thin_cells": thin_cells,
                    "empty_cells": empty_cells,
                    "m100_grounded_counts": m100_rows,
                    "m100_grounded_total": m100_total,
                },
                indent=2,
            )
        )
        return

    typer.echo(f"QCAT x role task counts ({total_tasks} task{'s' if total_tasks != 1 else ''})\n")
    _emit(main_rows, ["qcat", *codes, "total"], False)

    typer.echo(
        f"\nThin cells ({len(thin_cells)} of {cells_total}, <=1 task): {', '.join(thin_cells)}"
        if thin_cells
        else f"\nNo thin cells: all {cells_total} have more than one task."
    )
    if empty_cells:
        typer.echo(
            f"Empty cells ({len(empty_cells)} of {cells_total}, no task at all): "
            f"{', '.join(empty_cells)}"
        )

    typer.echo(
        f"\nM100-grounded tasks ({m100_total} of the {total_tasks} above, "
        "real Marconi100 ExaData):\n"
    )
    _emit([r for r in m100_rows if r["total"] > 0], ["qcat", *codes, "total"], False)
