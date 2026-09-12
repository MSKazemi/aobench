"""``aobench new`` — scaffold a corpus contribution instead of hand-writing JSON.

``aobench list coverage`` will tell a would-be contributor that ``DOCS_DES`` is thin and
then abandon them: step one of *Adding a task* is "write the spec", and the spec has eight
required fields, twenty-five optional ones, a task_id convention that is nowhere in the
code, and ``gold_evidence_refs`` that must point at paths inside a snapshot they have to
explore by hand. Writing one task is a research problem; getting the *shape* of one right
should not be.

This command does the mechanical half. It picks the cell (or the thinnest one), allocates
the next free task_id, suggests the environment that comparable tasks already use, lists
the files that actually exist in that snapshot as candidate evidence, and emits a spec that
is structurally valid from the first byte. What it deliberately does **not** do is invent
the parts that carry the value — the question, the gold answer, and the evidence that
supports it are left as explicit ``TODO`` markers, because a task whose gold answer was
generated is worth nothing to a benchmark.

The cell/role/QCAT vocabulary is imported from :mod:`aobench.cli.list_cmd` rather than
restated, so "thin cell" can never mean two different things in two commands.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, Optional

import typer

from aobench.cli._common import available_env_ids, resolve_root
from aobench.cli.list_cmd import _QCAT_DESCRIPTIONS, _ROLE_CODES, _load_specs

new_app = typer.Typer(
    help="Scaffold a new task spec from the corpus conventions.",
    no_args_is_help=True,
)

# Reverse of list_cmd's role->code map. Built here rather than hard-coded so adding a role
# in one place keeps both directions consistent.
_CODE_TO_ROLE: dict[str, str] = {code: role for role, code in _ROLE_CODES.items()}

# Evidence-ref listing is a browsing aid, not an inventory: a snapshot with hundreds of
# telemetry files would bury the useful ones and the terminal output would be unreadable.
_MAX_EVIDENCE_SHOWN = 25

_TODO = "TODO"


def _resolve_cell(cell: Optional[str], qcat: Optional[str], role: Optional[str]) -> tuple[str, str]:
    """Return ``(qcat, role)`` from either ``--cell QCAT_CODE`` or the separate flags."""
    if cell:
        if qcat or role:
            typer.echo("Use --cell, or --qcat/--role, but not both.", err=True)
            raise typer.Exit(code=2)
        head, sep, code = cell.rpartition("_")
        if not sep:
            typer.echo(
                f"--cell must look like QCAT_ROLECODE, e.g. DOCS_DES (got {cell!r}).",
                err=True,
            )
            raise typer.Exit(code=2)
        qcat, role = head.upper(), code.upper()

    if not qcat or not role:
        typer.echo(
            "Say which cell to fill: --cell DOCS_DES, or --qcat DOCS --role system_designer,"
            "\nor --thinnest to let AOBench choose the emptiest cell.",
            err=True,
        )
        raise typer.Exit(code=2)

    qcat = qcat.upper()
    if qcat not in _QCAT_DESCRIPTIONS:
        typer.echo(
            f"Unknown QCAT {qcat!r}. Valid: {', '.join(sorted(_QCAT_DESCRIPTIONS))}",
            err=True,
        )
        raise typer.Exit(code=2)

    # Accept either the long role name or the three-letter column code, because the
    # coverage matrix prints codes and the spec field wants names.
    resolved = _CODE_TO_ROLE.get(role.upper()) or (role if role in _ROLE_CODES else None)
    if resolved is None:
        typer.echo(
            f"Unknown role {role!r}. Valid: {', '.join(_ROLE_CODES)}"
            f"\nor their codes: {', '.join(_ROLE_CODES.values())}",
            err=True,
        )
        raise typer.Exit(code=2)
    return qcat, resolved


def _thinnest_cell(specs: list[dict[str, Any]]) -> tuple[str, str]:
    """Pick the emptiest QCAT x role cell, ties broken alphabetically for determinism."""
    counts: Counter[tuple[str, str]] = Counter()
    for qcat in _QCAT_DESCRIPTIONS:
        for role in _ROLE_CODES:
            counts[(qcat, role)] = 0
    for spec in specs:
        key = (str(spec.get("qcat") or ""), str(spec.get("role") or ""))
        if key in counts:
            counts[key] += 1
    return min(counts, key=lambda k: (counts[k], k[0], k[1]))


def _next_task_id(specs: list[dict[str, Any]], qcat: str, role_code: str) -> str:
    """Allocate the next free ``<QCAT>_<ROLE>_<NNN>`` id.

    Scans the ids already in the corpus rather than counting files, so a gap left by a
    removed task is not silently reused and an ``M100_``-prefixed id cannot collide.
    """
    prefix = f"{qcat}_{role_code}_"
    used: set[int] = set()
    for spec in specs:
        task_id = str(spec.get("task_id", ""))
        if task_id.startswith(prefix):
            tail = task_id[len(prefix) :]
            if tail.isdigit():
                used.add(int(tail))
    nxt = next(n for n in range(1, 1000) if n not in used)
    return f"{prefix}{nxt:03d}"


def _suggest_env(specs: list[dict[str, Any]], qcat: str, role: str, root: Path) -> str:
    """Suggest the environment comparable tasks already use.

    Preference order: same QCAT *and* role, then same QCAT, then the first bundle. An
    author is far more likely to find usable evidence in a snapshot that already supports
    this kind of question than in an arbitrary one.
    """
    predicates: list[Callable[[dict[str, Any]], bool]] = [
        lambda s: s.get("qcat") == qcat and s.get("role") == role,
        lambda s: s.get("qcat") == qcat,
    ]
    for predicate in predicates:
        envs = Counter(
            str(s["environment_id"]) for s in specs if predicate(s) and s.get("environment_id")
        )
        if envs:
            return envs.most_common(1)[0][0]
    ids = available_env_ids(root)
    return ids[0] if ids else "env_01"


def _evidence_candidates(env_dir: Path) -> list[str]:
    """Relative paths of the files an author can cite as evidence in this snapshot."""
    if not env_dir.is_dir():
        return []
    skip = {"manifest.txt", "metadata.yaml"}
    return sorted(
        str(p.relative_to(env_dir))
        for p in env_dir.rglob("*")
        if p.is_file() and p.name not in skip and not p.name.startswith(".")
    )


def _skeleton(
    task_id: str,
    qcat: str,
    role: str,
    env_id: str,
    difficulty: str,
    answer_type: str,
) -> dict[str, Any]:
    """A structurally valid spec whose *semantic* fields are explicitly unfinished.

    ``validation_status`` and ``scoring_readiness`` start at ``not_started``/``blocked``
    on purpose: the schema already has vocabulary for "this task is not done yet", so a
    scaffold announces itself rather than looking like a finished task nobody reviewed.
    """
    tier = {"easy": 1, "medium": 2, "hard": 3, "adversarial": 3}[difficulty]
    return {
        "task_id": task_id,
        "title": f"{_TODO}: one-line summary of what is being asked",
        "query_text": f"{_TODO}: the question, in the words this role would actually use",
        "role": role,
        "qcat": qcat,
        "difficulty": difficulty,
        "difficulty_tier": tier,
        "environment_id": env_id,
        "expected_answer_type": answer_type,
        "gold_evidence_refs": [],
        "eval_criteria": {
            "evaluation_mode": "semantic_match",
            "gold_answer": (
                f"{_TODO}: the correct answer, and the reasoning an operator would use to "
                "reach it from the evidence in this snapshot"
            ),
            "required_evidence_refs": [],
        },
        "allowed_tools": [],
        "hard_fail_conditions": [],
        "aggregate_weight_profile": "alpha1_grounding",
        "benchmark_split": "dev",
        "validation_status": "not_started",
        "scoring_readiness": "blocked",
        "task_creation_date": date.today().isoformat(),
    }


@new_app.command("task")
def new_task(  # noqa: PLR0913  (each flag maps to one spec field; grouping them would hide that)
    cell: Optional[str] = typer.Option(
        None, "--cell", help="Cell to fill, as QCAT_ROLECODE, e.g. DOCS_DES."
    ),
    qcat: Optional[str] = typer.Option(None, "--qcat", help="Question category, e.g. DOCS."),
    role: Optional[str] = typer.Option(
        None, "--role", help="Role name (scientific_user) or code (USR)."
    ),
    thinnest: bool = typer.Option(
        False, "--thinnest", help="Fill the emptiest cell in the coverage matrix."
    ),
    env: Optional[str] = typer.Option(
        None, "--env", help="Environment id. Default: the one comparable tasks use."
    ),
    difficulty: str = typer.Option("medium", "--difficulty", help="easy|medium|hard|adversarial."),
    answer_type: str = typer.Option("diagnosis", "--answer-type", help="Expected answer type."),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write here instead of the corpus spec directory."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the spec, write nothing."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing file."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root", help="Corpus root."),
) -> None:
    """Scaffold a task spec for a QCAT x role cell.

    Fills in the mechanical parts — id, role, category, environment, and a valid shape —
    and leaves the question, the gold answer, and the evidence refs as TODO, because those
    are the parts that make a task worth having.

    Examples:

      aobench new task --thinnest

      aobench new task --cell DOCS_DES --env env_21

      aobench new task --qcat JOB --role sysadmin --difficulty hard --dry-run
    """
    if difficulty not in {"easy", "medium", "hard", "adversarial"}:
        typer.echo(
            f"Unknown difficulty {difficulty!r}. Valid: easy, medium, hard, adversarial.",
            err=True,
        )
        raise typer.Exit(code=2)

    root = resolve_root(benchmark_root)
    specs = _load_specs(root)

    if thinnest:
        if cell or qcat or role:
            typer.echo("--thinnest picks the cell for you; drop --cell/--qcat/--role.", err=True)
            raise typer.Exit(code=2)
        qcat_r, role_r = _thinnest_cell(specs)
        typer.echo(f"Thinnest cell: {qcat_r}_{_ROLE_CODES[role_r]}")
    else:
        qcat_r, role_r = _resolve_cell(cell, qcat, role)

    role_code = _ROLE_CODES[role_r]
    task_id = _next_task_id(specs, qcat_r, role_code)
    env_id = env or _suggest_env(specs, qcat_r, role_r, root)

    known_envs = available_env_ids(root)
    if known_envs and env_id not in known_envs:
        typer.echo(
            f"Unknown environment {env_id!r}. Run `aobench list envs` to see the {len(known_envs)} bundles.",
            err=True,
        )
        raise typer.Exit(code=2)

    spec = _skeleton(task_id, qcat_r, role_r, env_id, difficulty, answer_type)
    rendered = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"

    if dry_run:
        typer.echo(rendered, nl=False)
        return

    dest = Path(output) if output else root / "tasks" / "specs" / f"{task_id}.json"
    if dest.exists() and not force:
        typer.echo(f"{dest} already exists. Pass --force to overwrite.", err=True)
        raise typer.Exit(code=1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(rendered, encoding="utf-8")

    typer.echo(f"\nCreated {dest}")
    typer.echo(f"  task_id     {task_id}")
    typer.echo(f"  cell        {qcat_r} x {role_r}  ({_QCAT_DESCRIPTIONS.get(qcat_r, '')})")
    typer.echo(f"  environment {env_id}")

    candidates = _evidence_candidates(root / "environments" / env_id)
    if candidates:
        shown = candidates[:_MAX_EVIDENCE_SHOWN]
        typer.echo(f"\nEvidence available in {env_id} ({len(candidates)} files):")
        for path in shown:
            typer.echo(f"  {path}")
        if len(candidates) > len(shown):
            typer.echo(f"  ... and {len(candidates) - len(shown)} more")
        typer.echo(
            "\nCite these in gold_evidence_refs, optionally with an anchor:"
            '\n  "slurm/job_details.json#oom_evidence"'
        )

    if output is None:
        # The scaffold is now a corpus file, so `run all --split dev` will pick it up and
        # score it like any other task -- and an unfinished one scores *well*: an empty
        # `expected_tool_calls` currently earns a vacuous `tool_use: 1.0`, which can make a
        # placeholder the highest-scoring task in the run (#75). Until `scoring_readiness`
        # actually gates run selection, the honest thing is to say so here rather than let
        # a contributor's first benchmark run be quietly wrong.
        typer.echo(
            f"\nNote: {dest} is in the corpus now, so `aobench run all --split dev` will"
            "\ninclude and score it. An unfinished task still gets a score, and an empty"
            "\n`expected_tool_calls` scores *higher* than a real task (#75) — so finish it,"
            "\nor delete the file, before you run the benchmark."
        )

    typer.echo(
        f"\nNext, replace every {_TODO} in the file — the question, the gold answer, and the"
        "\nevidence that supports it. Then:"
        "\n  aobench validate benchmark        # does it load and type-check?"
        f"\n  aobench run task --task {task_id} --env {env_id} --adapter direct_qa"
        "\n                                    # the tool-free baseline should FAIL it"
        "\n\nThe full workflow, including the review checklist, is in"
        "\ndocs/guides/adding-a-task.md."
    )
