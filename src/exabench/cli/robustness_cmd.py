"""exabench robustness — run a task N times and report score variance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

robustness_app = typer.Typer(help="Measure score consistency across repeated runs.")

_OPT_TASK = typer.Option("--task", "-t", help="Task ID, e.g. JOB_USR_001")
_OPT_ENV = typer.Option("--env", "-e", help="Environment ID, e.g. env_01")
_OPT_ADAPTER = typer.Option(
    "--adapter", "-a", help="Adapter name, e.g. direct_qa or openai:gpt-4o"
)
_OPT_N = typer.Option("--n", help="Number of repeated runs (≥ 8 recommended for pass^k)")
_OPT_THRESHOLD = typer.Option(
    "--pass-threshold", help="Min aggregate_score to count a run as passing"
)
_OPT_OUTPUT = typer.Option("--output", "-o", help="Write robustness JSON to this path")
_OPT_BENCH_ROOT = typer.Option("--benchmark-root", help="Benchmark root directory")
_OPT_OUT_ROOT = typer.Option("--output-root", help="Run output root directory")


def _print_stats(stats: dict[str, Any]) -> None:
    """Print robustness statistics to stdout."""
    typer.echo(f"\n{'─' * 50}")
    typer.echo(f"Task         : {stats['task_id']}")
    typer.echo(f"Runs         : {stats['n_runs']}  (passing: {stats['n_passing']})")
    typer.echo(f"Threshold    : {stats['pass_threshold']}")
    typer.echo("")
    typer.echo("pass^k (τ-bench reliability metric):")
    for k, v in stats["pass_k"].items():
        bar = "█" * int(v * 20)
        typer.echo(f"  pass^{k:<2}  {v:.4f}  {bar}")
    typer.echo("")
    typer.echo(f"Mean score   : {stats['mean_score']:.4f}")
    typer.echo(f"Std dev      : {stats['std_dev']:.4f}")
    typer.echo(f"Range        : {stats['min_score']:.4f} – {stats['max_score']:.4f}")
    typer.echo(f"Robustness   : {stats['robustness_score']:.4f}  (1 − σ)")
    typer.echo(f"{'─' * 50}\n")


@robustness_app.command("task")
def robustness_task(  # noqa: PLR0913
    task: Annotated[str, _OPT_TASK],
    env: Annotated[str, _OPT_ENV],
    adapter: Annotated[str, _OPT_ADAPTER] = "direct_qa",
    n: Annotated[int, _OPT_N] = 8,
    pass_threshold: Annotated[float, _OPT_THRESHOLD] = 0.5,
    output: Annotated[str | None, _OPT_OUTPUT] = None,
    benchmark_root: Annotated[str, _OPT_BENCH_ROOT] = "benchmark",
    output_root: Annotated[str, _OPT_OUT_ROOT] = "data/runs",
) -> None:
    """Run TASK on ENV with ADAPTER exactly N times and report pass^k + variance.

    pass^k is the probability that ALL k independent runs succeed (τ-bench metric).
    pass^8 < 0.25 is the critical production-reliability threshold from CLEAR.

    Recommended: --n 8 or higher to compute all standard k values (1, 2, 4, 8).
    """
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter  # noqa: PLC0415
    from exabench.runners.runner import BenchmarkRunner  # noqa: PLC0415
    from exabench.scorers.robustness_scorer import compute_robustness  # noqa: PLC0415
    from exabench.utils.ids import make_run_id  # noqa: PLC0415

    # Build adapter
    if adapter == "direct_qa":
        _adapter = DirectQAAdapter()
    elif adapter.startswith("openai"):
        from exabench.adapters.openai_adapter import OpenAIAdapter  # noqa: PLC0415
        model = adapter.split(":", 1)[1] if ":" in adapter else "gpt-4o"
        _adapter = OpenAIAdapter(model=model)
    elif adapter.startswith("anthropic"):
        from exabench.adapters.anthropic_adapter import AnthropicAdapter  # noqa: PLC0415
        model = adapter.split(":", 1)[1] if ":" in adapter else "claude-sonnet-4-6"
        _adapter = AnthropicAdapter(model=model)
    else:
        typer.echo(f"Unknown adapter: {adapter}", err=True)
        raise typer.Exit(1)

    typer.echo(
        f"\nRobustness run: {task} @ {env}"
        f"  adapter={adapter}  n={n}  threshold={pass_threshold}\n"
    )

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
        passed = "✓" if result.aggregate_score >= pass_threshold else "✗"
        typer.echo(f"  Run {i + 1}/{n}  score={result.aggregate_score:.4f}  {passed}")

    stats = compute_robustness(results, pass_threshold=pass_threshold)
    _print_stats(stats)

    if output:
        Path(output).write_text(json.dumps(stats, indent=2), encoding="utf-8")
        typer.echo(f"Written: {output}")


def _print_suite_stats(suite: dict) -> None:
    """Print suite-level robustness summary to stdout."""
    typer.echo(f"\n{'═' * 60}")
    typer.echo("Suite robustness summary")
    typer.echo(f"{'─' * 60}")
    typer.echo(f"Tasks evaluated : {len(suite['tasks'])}")
    typer.echo(f"Mean robustness : {suite['mean_robustness_score']:.4f}  (1 − σ)")
    typer.echo("")
    typer.echo("Mean pass^k across all tasks:")
    for k, v in suite["mean_pass_k"].items():
        bar = "█" * int(v * 20)
        typer.echo(f"  pass^{k:<2}  {v:.4f}  {bar}")
    if suite.get("total_cost_usd") is not None:
        typer.echo(f"\nTotal cost      : ${suite['total_cost_usd']:.4f}")
    if suite.get("mean_latency_seconds") is not None:
        typer.echo(f"Mean latency    : {suite['mean_latency_seconds']:.3f}s")
    typer.echo("")
    typer.echo("Per-task pass^1 (success rate):")
    for task_id, stats in sorted(suite["tasks"].items()):
        p1 = stats["pass_k"].get(1, 0.0)
        bar = "█" * int(p1 * 20)
        typer.echo(f"  {task_id:<20} {p1:.4f}  {bar}")
    typer.echo(f"{'═' * 60}\n")


@robustness_app.command("all")
def robustness_all(  # noqa: PLR0913
    adapter: Annotated[str, _OPT_ADAPTER] = "direct_qa",
    n: Annotated[int, _OPT_N] = 8,
    pass_threshold: Annotated[float, _OPT_THRESHOLD] = 0.5,
    output: Annotated[str | None, _OPT_OUTPUT] = None,
    benchmark_root: Annotated[str, _OPT_BENCH_ROOT] = "benchmark",
    output_root: Annotated[str, _OPT_OUT_ROOT] = "data/runs",
    split: Annotated[str | None, typer.Option("--split", help="Only run tasks in this benchmark_split (dev/public_test/hidden_test)")] = None,
) -> None:
    """Run ALL benchmark tasks N times each and report suite-level pass^k.

    Produces a robustness JSON with per-task pass^k (k=1,2,4,8), score
    variance, and cost/latency stats across all N*|tasks| runs.

    Recommended: --n 8 to compute the full k=(1,2,4,8) profile.
    Use --split dev for a quick smoke-test (12 tasks × N runs).
    """
    from exabench.loaders.task_loader import load_tasks_from_dir  # noqa: PLC0415
    from exabench.runners.runner import BenchmarkRunner  # noqa: PLC0415
    from exabench.scorers.robustness_scorer import compute_robustness_suite  # noqa: PLC0415
    from exabench.utils.ids import make_run_id  # noqa: PLC0415

    if adapter == "direct_qa":
        from exabench.adapters.direct_qa_adapter import DirectQAAdapter  # noqa: PLC0415
        _adapter = DirectQAAdapter()
    elif adapter.startswith("openai"):
        from exabench.adapters.openai_adapter import OpenAIAdapter  # noqa: PLC0415
        model = adapter.split(":", 1)[1] if ":" in adapter else "gpt-4o"
        _adapter = OpenAIAdapter(model=model)
    elif adapter.startswith("anthropic"):
        from exabench.adapters.anthropic_adapter import AnthropicAdapter  # noqa: PLC0415
        model = adapter.split(":", 1)[1] if ":" in adapter else "claude-sonnet-4-6"
        _adapter = AnthropicAdapter(model=model)
    else:
        typer.echo(f"Unknown adapter: {adapter}", err=True)
        raise typer.Exit(1)

    specs_dir = Path(benchmark_root) / "tasks" / "specs"
    all_tasks = load_tasks_from_dir(specs_dir)
    if not all_tasks:
        typer.echo(f"No tasks found in {specs_dir}", err=True)
        raise typer.Exit(1)

    tasks = all_tasks
    if split:
        tasks = [t for t in all_tasks if t.benchmark_split == split]
        if not tasks:
            typer.echo(f"No tasks with benchmark_split='{split}'", err=True)
            raise typer.Exit(1)
        typer.echo(f"Filtered to {len(tasks)} tasks with split={split}")

    total_runs = len(tasks) * n
    typer.echo(
        f"\nRobustness suite: {len(tasks)} tasks × {n} runs = {total_runs} total"
        f"  adapter={adapter}  threshold={pass_threshold}\n"
    )

    runner = BenchmarkRunner(
        adapter=_adapter,
        benchmark_root=Path(benchmark_root),
        output_root=Path(output_root),
    )

    results_by_task: dict[str, list] = {t.task_id: [] for t in tasks}
    completed = 0
    for task in tasks:
        typer.echo(f"  {task.task_id} @ {task.environment_id}  ({n} runs):")
        for i in range(n):
            run_id = make_run_id()
            try:
                result = runner.run(task.task_id, task.environment_id, run_id=run_id)
                results_by_task[task.task_id].append(result)
                passed = "✓" if (result.aggregate_score or 0) >= pass_threshold else "✗"
                typer.echo(f"    run {i + 1}/{n}  score={result.aggregate_score:.4f}  {passed}", nl=False)
                if result.cost_estimate_usd is not None:
                    typer.echo(f"  ${result.cost_estimate_usd:.4f}", nl=False)
                typer.echo("")
                completed += 1
            except Exception as e:
                typer.echo(f"    run {i + 1}/{n}  FAILED: {e}", err=True)

    suite = compute_robustness_suite(results_by_task, pass_threshold=pass_threshold)
    _print_suite_stats(suite)

    if output:
        Path(output).write_text(json.dumps(suite, indent=2), encoding="utf-8")
        typer.echo(f"Written: {output}")
    elif not output:
        default_path = Path(output_root) / "robustness_suite.json"
        default_path.parent.mkdir(parents=True, exist_ok=True)
        default_path.write_text(json.dumps(suite, indent=2), encoding="utf-8")
        typer.echo(f"Written: {default_path}")
