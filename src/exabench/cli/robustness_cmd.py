"""exabench robustness — run a task N times and report score variance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

robustness_app = typer.Typer(help="Measure score consistency across repeated runs.")


@robustness_app.command("task")
def robustness_task(
    task: Annotated[str, typer.Option("--task", "-t", help="Task ID, e.g. JOB_USR_001")],
    env: Annotated[str, typer.Option("--env", "-e", help="Environment ID, e.g. env_01")],
    adapter: Annotated[str, typer.Option("--adapter", "-a", help="Adapter name, e.g. direct_qa or openai:gpt-4o")] = "direct_qa",
    n: Annotated[int, typer.Option("--n", help="Number of repeated runs")] = 5,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write robustness JSON to this path")] = None,
    benchmark_root: Annotated[str, typer.Option("--benchmark-root", help="Benchmark root directory")] = "benchmark",
    output_root: Annotated[str, typer.Option("--output-root", help="Run output root directory")] = "data/runs",
) -> None:
    """Run TASK on ENV with ADAPTER exactly N times and report score variance.

    A robustness_score of 1.0 means perfectly consistent results.
    Lower scores indicate the adapter produces variable answers for the same query.
    """
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter
    from exabench.runners.runner import BenchmarkRunner
    from exabench.scorers.robustness_scorer import compute_robustness
    from exabench.utils.ids import make_run_id

    # Build adapter
    if adapter == "direct_qa":
        _adapter = DirectQAAdapter()
    elif adapter.startswith("openai"):
        from exabench.adapters.openai_adapter import OpenAIAdapter
        model = adapter.split(":", 1)[1] if ":" in adapter else "gpt-4o"
        _adapter = OpenAIAdapter(model=model)
    else:
        typer.echo(f"Unknown adapter: {adapter}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\nRobustness run: {task} @ {env}  adapter={adapter}  n={n}\n")

    runner = BenchmarkRunner(
        adapter=_adapter,
        benchmark_root=benchmark_root,
        output_root=output_root,
    )

    results = []
    for i in range(n):
        run_id = make_run_id()
        result = runner.run(task, env, run_id=run_id)
        results.append(result)
        typer.echo(f"  Run {i + 1}/{n}  score={result.aggregate_score:.4f}")

    stats = compute_robustness(results)

    typer.echo(f"\n{'─'*50}")
    typer.echo(f"Task         : {stats['task_id']}")
    typer.echo(f"Runs         : {stats['n_runs']}")
    typer.echo(f"Mean score   : {stats['mean_score']:.4f}")
    typer.echo(f"Std dev      : {stats['std_dev']:.4f}")
    typer.echo(f"Range        : {stats['min_score']:.4f} – {stats['max_score']:.4f}")
    typer.echo(f"Robustness   : {stats['robustness_score']:.4f}")
    typer.echo(f"{'─'*50}\n")

    if output:
        Path(output).write_text(json.dumps(stats, indent=2))
        typer.echo(f"Written: {output}")
