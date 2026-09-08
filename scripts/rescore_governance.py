"""Re-score governance on stored run traces with the CURRENT (fixed) scorer.

Motivation
----------
The paper's governance numbers (GPT-4o 0.216, mini 0.138, mini+RBAC 0.276) were
locked 2026-05-25, ~2.5 weeks BEFORE the governance-scorer fix committed on
2026-06-11 (75c9cc0, ``_parse_tool_method``). Before that fix the forbidden-call
check compared the raw ``tool_name`` against ``allowed_tools``; the openai adapter
records calls as ``tool__method`` (e.g. ``slurm__query_jobs``), so every
in-allowlist call was mis-flagged as forbidden (0.50 penalty each; two -> hard
fail -> governance 0). Direction of the error: governance UNDERSTATED.

The shipped ``aobench rescore`` command does NOT actually re-score — it copies the
pre-existing scores straight out of each trace file. This script genuinely replays
each stored ``Trace`` through the current ``GovernanceScorer`` and recomputes the
paper statistics, so the corrected magnitude can be measured without any model calls.

Usage
-----
    uv run python -m scripts.rescore_governance \\
        --run-dir data/runs/<gpt4o_run_id> --label GPT-4o \\
        --run-dir data/runs/<mini_run_id>  --label GPT-4o-mini \\
        --benchmark-root benchmark \\
        --old 0.216 --old 0.138

Each ``--run-dir`` is paired positionally with a ``--label`` and (optionally) an
``--old`` reference mean for side-by-side comparison. Writes a JSON report and
prints a comparison table. No agent/judge calls are made.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import typer

from aobench.loaders.task_loader import load_task
from aobench.schemas.trace import Trace
from aobench.scorers.governance_scorer import GovernanceScorer

app = typer.Typer(help="Re-score governance on stored traces with the fixed scorer.")


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for proportion k/n (matches compute_governance_ci.py)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _rescore_run(run_dir: Path, benchmark_root: Path) -> dict:
    """Replay every stored trace in RUN_DIR through the fixed GovernanceScorer."""
    traces_dir = run_dir / "traces"
    if not traces_dir.is_dir():
        raise typer.BadParameter(f"no traces/ subdir in {run_dir}")
    trace_files = sorted(traces_dir.glob("*_trace.json"))
    if not trace_files:
        raise typer.BadParameter(f"no *_trace.json files in {traces_dir}")

    scorer = GovernanceScorer()
    specs_dir = benchmark_root / "tasks" / "specs"
    per_task: list[dict] = []
    for tp in trace_files:
        task_id = tp.stem.removesuffix("_trace")
        trace = Trace.model_validate_json(tp.read_text(encoding="utf-8"))
        task = load_task(specs_dir / f"{task_id}.json")
        out = scorer.score(task, trace)
        per_task.append(
            {
                "task_id": task_id,
                "governance": out.score,
                "hard_fail": bool(out.hard_fail),
                "notes": out.notes,
            }
        )

    n = len(per_task)
    mean = sum(t["governance"] for t in per_task) / n if n else 0.0
    # hard-fail rate = fraction with governance == 0.0 (RBAC violation)
    n_hard_fail = sum(1 for t in per_task if t["governance"] == 0.0)
    # RBAC-compliance proportion = fraction with governance == 1.0 (CI basis in paper script)
    n_compliant = sum(1 for t in per_task if t["governance"] == 1.0)
    lo, hi = wilson_ci(n_compliant, n)
    return {
        "n": n,
        "governance_mean": round(mean, 4),
        "hard_fail_rate": round(n_hard_fail / n, 4) if n else 0.0,
        "compliance_rate": round(n_compliant / n, 4) if n else 0.0,
        "compliance_ci95": [round(lo, 4), round(hi, 4)],
        "per_task": per_task,
    }


@app.command()
def main(
    run_dir: list[str] = typer.Option(..., "--run-dir", help="Run directory (repeatable)."),  # noqa: B008
    label: list[str] = typer.Option(None, "--label", help="Label per run-dir (repeatable)."),  # noqa: B008
    old: list[float] = typer.Option(None, "--old", help="Old governance mean per run-dir (repeatable)."),  # noqa: B008
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root"),
    output: str = typer.Option(
        "data/paper/governance_rescore_report.json", "--output", "-o"
    ),
) -> None:
    broot = Path(benchmark_root)
    labels = label or [Path(r).name for r in run_dir]
    olds = old or [None] * len(run_dir)
    if len(labels) != len(run_dir) or len(olds) != len(run_dir):
        raise typer.BadParameter("--label / --old counts must match --run-dir count")

    report = []
    typer.echo(f"{'label':<20} {'n':>4} {'old':>8} {'new':>8} {'Δ':>8} {'fail%':>7} {'CI95':>18}")
    typer.echo("-" * 78)
    for rd, lb, ov in zip(run_dir, labels, olds):
        res = _rescore_run(Path(rd), broot)
        res["label"] = lb
        res["old_governance_mean"] = ov
        delta = None if ov is None else round(res["governance_mean"] - ov, 4)
        res["delta_vs_old"] = delta
        report.append(res)
        ci = f"[{res['compliance_ci95'][0]:.3f},{res['compliance_ci95'][1]:.3f}]"
        typer.echo(
            f"{lb:<20} {res['n']:>4} {ov!s:>8} {res['governance_mean']:>8.3f} "
            f"{delta!s:>8} {res['hard_fail_rate']*100:>6.1f}% {ci:>18}"
        )

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(f"\nReport written -> {out_path}")


if __name__ == "__main__":
    app()
