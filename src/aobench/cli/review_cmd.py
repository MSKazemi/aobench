"""``aobench review task`` — run the corpus review checklist against ONE task.

Every validator in this project is corpus-wide. ``validate benchmark`` loads all 88 tasks,
``validate tasks`` prints an 88-row T1–T10 table, ``validate authoring`` cross-compares the
whole corpus. That is right for CI and wrong for the person who just wrote their first task:
they get a global pass/fail in which their own work is one line, and no answer to the only
question they have, which is "is *mine* right?".

It is also what makes reviewing corpus PRs a manual job. `docs/guides/adding-a-task.md`
publishes the checklist a reviewer applies, and until now that checklist was enforced by the
maintainer's attention, one task at a time. Most of its items are mechanical — does the
evidence exist, are the tools ones this role is actually permitted, is this a near-duplicate
of a task we already have — and a mechanical check belongs in software, so the human review
can be spent on the half that genuinely needs an operator's judgement: whether the question
is real and whether the gold answer is right.

The checks here deliberately mirror the published checklist item for item, so a contributor
running this before opening a PR sees the same list the reviewer will.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Optional

import typer
import yaml

from aobench.cli._common import require_task_spec, resolve_root

review_app = typer.Typer(
    help="Review a single task against the corpus checklist.",
    no_args_is_help=True,
)

# Outcomes. FAIL blocks, WARN is a judgement call for the reviewer, TODO means the author
# has not finished, and SKIP means the check could not run (never silently "fine").
_PASS, _FAIL, _WARN, _TODO, _SKIP = "PASS", "FAIL", "WARN", "TODO", "SKIP"

_MARKS = {_PASS: "✓", _FAIL: "✗", _WARN: "!", _TODO: "…", _SKIP: "-"}

# Above this cosine similarity on the authoring feature vector, two tasks are similar
# enough that a reviewer should look at whether the new one adds coverage. It is a prompt
# for a human, never a rejection: the vector is coarse by design.
_DUPLICATE_SIMILARITY = 0.995

_TOOL_FAMILIES = {"slurm", "telemetry", "docs", "rbac", "facility"}


class _Check:
    """One checklist row: what was checked, how it came out, and what to do about it."""

    def __init__(self, item: str, status: str, detail: str = "") -> None:
        self.item = item
        self.status = status
        self.detail = detail

    def as_dict(self) -> dict[str, str]:
        return {"item": self.item, "status": self.status, "detail": self.detail}


def _feature_vector(spec: dict[str, Any]) -> list[float]:
    """Coarse authoring fingerprint, matching ``validate authoring``'s independence check.

    Deliberately the same shape as the existing corpus-wide check so the two cannot
    disagree about what "similar" means.
    """
    tier = {"easy": 1, "medium": 2, "hard": 3, "adversarial": 3}.get(
        str(spec.get("difficulty", "easy")), 1
    )
    refs = spec.get("gold_evidence_refs") or []
    query = spec.get("query_text") or ""
    gold = (spec.get("eval_criteria") or {}).get("gold_answer") or ""
    tools = spec.get("allowed_tools") or []
    return [
        min(tier / 3.0, 1.0),
        min(len(refs) / 10.0, 1.0),
        min(len(query) / 500.0, 1.0),
        min(len(gold) / 1000.0, 1.0),
        1.0 if "slurm" in tools else 0.0,
    ]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _check_schema(spec: dict[str, Any]) -> _Check:
    from pydantic import ValidationError

    from aobench.schemas.task import TaskSpec

    try:
        TaskSpec.model_validate(spec)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first.get("loc", ()))
        return _Check("Schema", _FAIL, f"{where}: {first.get('msg', 'invalid')}")
    return _Check("Schema", _PASS, "TaskSpec accepts it")


def _check_unfinished(spec: dict[str, Any]) -> _Check:
    """Catch a scaffold that was submitted before its author filled it in."""
    gold = (spec.get("eval_criteria") or {}).get("gold_answer") or ""
    todo_fields = [
        name
        for name, value in (
            ("title", spec.get("title") or ""),
            ("query_text", spec.get("query_text") or ""),
            ("eval_criteria.gold_answer", gold),
        )
        if str(value).lstrip().startswith("TODO")
    ]
    if todo_fields:
        return _Check("Finished", _TODO, f"still scaffold text: {', '.join(todo_fields)}")
    if spec.get("validation_status") == "not_started":
        return _Check("Finished", _TODO, "validation_status is still not_started")
    return _Check("Finished", _PASS, "no scaffold markers left")


def _check_environment(spec: dict[str, Any], root: Path) -> tuple[_Check, Optional[Path]]:
    env_id = str(spec.get("environment_id") or "")
    if not env_id:
        return _Check("Environment", _FAIL, "environment_id is empty"), None
    env_path = root / "environments" / env_id
    if not env_path.is_dir():
        return _Check("Environment", _FAIL, f"no such bundle: {env_id}"), None
    return _Check("Environment", _PASS, env_id), env_path


def _check_evidence(spec: dict[str, Any], env_path: Optional[Path]) -> _Check:
    """The gold answer must be supported by evidence that exists in the named bundle."""
    refs = spec.get("gold_evidence_refs") or []
    if env_path is None:
        return _Check("Evidence", _SKIP, "environment could not be resolved")
    if not refs:
        return _Check(
            "Evidence",
            _WARN,
            "gold_evidence_refs is empty — the answer is not anchored to the snapshot",
        )

    missing = [r for r in refs if not (env_path / str(r).split("#")[0]).exists()]
    if missing:
        return _Check("Evidence", _FAIL, f"not in the bundle: {', '.join(missing)}")

    required = set((spec.get("eval_criteria") or {}).get("required_evidence_refs") or [])
    stray = sorted(required - set(refs))
    if stray:
        return _Check(
            "Evidence",
            _FAIL,
            f"required_evidence_refs not listed in gold_evidence_refs: {', '.join(stray)}",
        )
    return _Check("Evidence", _PASS, f"{len(refs)} ref(s), all present")


def _check_tools(spec: dict[str, Any], env_path: Optional[Path]) -> _Check:
    """``allowed_tools`` must reflect the role's real permissions, not the task's convenience.

    This is the checklist item most likely to be got wrong in good faith — it is tempting to
    grant whatever the task happens to need — and it is the one that quietly weakens the
    governance dimension, which is the point of the benchmark.
    """
    tools = spec.get("allowed_tools") or []
    if not tools:
        return _Check("Tools", _WARN, "allowed_tools is empty — the agent gets no tools")

    unknown = sorted(set(tools) - _TOOL_FAMILIES)
    if unknown:
        return _Check(
            "Tools",
            _FAIL,
            f"unknown tool famil{'y' if len(unknown) == 1 else 'ies'}: {', '.join(unknown)}",
        )

    if env_path is None:
        return _Check("Tools", _SKIP, "environment could not be resolved")
    policy_file = env_path / "policy" / "rbac_policy.yaml"
    if not policy_file.is_file():
        return _Check("Tools", _SKIP, "bundle has no policy/rbac_policy.yaml")

    policy = yaml.safe_load(policy_file.read_text(encoding="utf-8")) or {}
    role = str(spec.get("role") or "")
    role_policy = (policy.get("roles") or {}).get(role)
    if role_policy is None:
        return _Check("Tools", _WARN, f"{role} is not described in this bundle's RBAC policy")

    if "allowed_tools" not in role_policy:
        return _Check("Tools", _SKIP, f"policy does not list allowed_tools for {role}")
    permitted = set(role_policy.get("allowed_tools") or [])
    if "*" in permitted:
        return _Check("Tools", _PASS, f"{role} holds the wildcard in this bundle")

    over = sorted(set(tools) - permitted)
    if over:
        # WARN, not FAIL: nothing in the engine intersects allowed_tools with this policy
        # -- ToolRegistry gates on the task's list alone and each tool enforces the role
        # internally -- so an over-grant is a question for a reviewer, not a proven defect.
        return _Check(
            "Tools",
            _WARN,
            f"grants {', '.join(over)}, which this bundle's policy does not list for "
            f"{role} (policy: {', '.join(sorted(permitted)) or 'none'})",
        )
    return _Check("Tools", _PASS, f"within {role}'s permissions")


def _check_duplication(spec: dict[str, Any], corpus: list[dict[str, Any]]) -> _Check:
    """A task earns its place by adding coverage, not by existing."""
    task_id = spec.get("task_id")
    mine = _feature_vector(spec)
    same_cell = [
        other
        for other in corpus
        if other.get("task_id") != task_id
        and other.get("qcat") == spec.get("qcat")
        and other.get("role") == spec.get("role")
    ]
    if not same_cell:
        return _Check("Coverage", _PASS, "first task in this cell")

    nearest, score = None, 0.0
    for other in same_cell:
        sim = _cosine(mine, _feature_vector(other))
        if sim > score:
            nearest, score = other.get("task_id"), sim
    if score >= _DUPLICATE_SIMILARITY:
        return _Check(
            "Coverage",
            _WARN,
            f"very close to {nearest} (similarity {score:.3f}) — does it add coverage?",
        )
    return _Check("Coverage", _PASS, f"{len(same_cell)} sibling(s), nearest {score:.3f}")


def _check_scoring(spec: dict[str, Any]) -> _Check:
    """Prefer deterministic scoring; a rubric costs an LLM judge call on every run."""
    mode = (spec.get("hybrid_scoring") or {}).get("scoring_mode")
    if mode == "rubric":
        return _Check("Scoring", _WARN, "rubric mode — is a deterministic check genuinely impossible?")
    evaluation = (spec.get("eval_criteria") or {}).get("evaluation_mode")
    if not evaluation:
        return _Check("Scoring", _WARN, "no evaluation_mode set")
    return _Check("Scoring", _PASS, str(mode or evaluation))


@review_app.command("task")
def review_task(
    task: str = typer.Argument(..., help="Task ID (JOB_USR_001) or a path to a spec file."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root", help="Corpus root."),
    as_json: bool = typer.Option(False, "--json", help="Emit the checklist as JSON."),
) -> None:
    """Run the corpus review checklist against one task.

    Mirrors the checklist in `docs/guides/adding-a-task.md`, so running this before you open
    a pull request shows you the same list the reviewer will work through.

    Exits non-zero if any check FAILs. ``WARN`` and ``TODO`` are reported but do not fail —
    they are the rows a human still has to judge.
    """
    root = resolve_root(benchmark_root)

    candidate = Path(task)
    spec_path = candidate if candidate.is_file() else require_task_spec(root, task)
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        typer.echo(f"{spec_path}: not valid JSON — {exc}", err=True)
        raise typer.Exit(code=2) from exc

    corpus: list[dict[str, Any]] = []
    for path in sorted((root / "tasks" / "specs").glob("*.json")):
        try:
            corpus.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:  # a broken sibling must not hide this task's report
            continue

    env_check, env_path = _check_environment(spec, root)
    checks = [
        _check_schema(spec),
        _check_unfinished(spec),
        env_check,
        _check_evidence(spec, env_path),
        _check_tools(spec, env_path),
        _check_scoring(spec),
        _check_duplication(spec, corpus),
    ]

    failed = [c for c in checks if c.status == _FAIL]
    open_rows = [c for c in checks if c.status in (_WARN, _TODO)]

    if as_json:
        typer.echo(
            json.dumps(
                {
                    "task_id": spec.get("task_id"),
                    "spec_path": str(spec_path),
                    "checks": [c.as_dict() for c in checks],
                    "failed": len(failed),
                    "needs_judgement": len(open_rows),
                    "ok": not failed,
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"\nReview: {spec.get('task_id', spec_path.stem)}  ({spec_path})\n")
        width = max(len(c.item) for c in checks)
        for check in checks:
            typer.echo(f"  {_MARKS[check.status]} {check.item:<{width}}  {check.detail}")

        typer.echo("")
        if failed:
            typer.echo(f"{len(failed)} check(s) failed — fix these before opening a PR.")
        elif open_rows:
            typer.echo(
                f"No failures. {len(open_rows)} row(s) need a human judgement, "
                "which is what review is for."
            )
        else:
            typer.echo("All mechanical checks pass.")
        typer.echo(
            "\nStill only a human can answer: is this a question the role would really ask,"
            "\nand is the gold answer right? Two commands that help:"
            f"\n  aobench run task --task {spec.get('task_id')} "
            f"--env {spec.get('environment_id')} --adapter direct_qa   # should FAIL"
            "\n  (then the same with a real model — it should be passable)"
        )

    if failed:
        raise typer.Exit(code=1)
