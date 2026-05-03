"""exabench run — run a benchmark task against an environment."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from exabench.utils.logging import configure_logging

run_app = typer.Typer(help="Run benchmark tasks.")

# ---------------------------------------------------------------------------
# Model registry — maps short token → (AdapterClass, model_name)
# ---------------------------------------------------------------------------

_MODEL_REGISTRY: dict[str, tuple[str, str]] = {
    "direct_qa":     ("DirectQAAdapter", "direct_qa"),
    "gpt-4o":        ("OpenAIAdapter",   "gpt-4o"),        # Azure: resolves via AZURE_COORDINATOR_DEPLOYMENT
    "gpt-4o-mini":   ("OpenAIAdapter",   "gpt-4o-mini"),   # Azure: resolves via AZURE_SUBAGENT_DEPLOYMENT
    "llama-3.3-70b": ("OpenAIAdapter",   "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
}

# Azure deployment name overrides — read once from env at import time so that
# smoke tests can patch os.environ before importing this module.
import os as _os
_AZURE_DEPLOYMENT_MAP: dict[str, str] = {
    "gpt-4o":      _os.environ.get("AZURE_COORDINATOR_DEPLOYMENT", "gpt-4o"),
    "gpt-4o-mini": _os.environ.get("AZURE_SUBAGENT_DEPLOYMENT", "gpt-4o-mini"),
}


def resolve_model(token: str) -> tuple[type, str]:
    """Map a model token to (AdapterClass, model_name).

    Raises SystemExit with a helpful message for unknown tokens.
    """
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter
    from exabench.adapters.openai_adapter import OpenAIAdapter

    _CLASS_MAP = {
        "DirectQAAdapter": DirectQAAdapter,
        "OpenAIAdapter": OpenAIAdapter,
    }

    entry = _MODEL_REGISTRY.get(token)
    if entry is None:
        valid = ", ".join(sorted(_MODEL_REGISTRY))
        typer.echo(
            f"Unknown model token '{token}'. Valid tokens: {valid}",
            err=True,
        )
        raise typer.Exit(1)

    class_name, model_name = entry
    return _CLASS_MAP[class_name], model_name


def _build_adapter_from_token(token: str):
    """Instantiate an adapter from a model registry token.

    For Azure deployments, gpt-4o and gpt-4o-mini resolve to the names in
    AZURE_COORDINATOR_DEPLOYMENT / AZURE_SUBAGENT_DEPLOYMENT respectively.
    """
    import os
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    try:
        load_dotenv()
    except Exception:  # noqa: BLE001
        pass
    adapter_class, model_name = resolve_model(token)
    if adapter_class.__name__ == "DirectQAAdapter":
        return adapter_class()
    # Resolve Azure deployment name override if on Azure
    if os.environ.get("AZURE_OPENAI_ENDPOINT"):
        model_name = _AZURE_DEPLOYMENT_MAP.get(token, model_name)
    return adapter_class(model=model_name)


def _load_system_prompt_prefix(path: str | None, task) -> str:
    """Load and render the system-prompt prefix file for a given task.

    Substitutes {{role}}, {{permitted_tools_csv}}, {{forbidden_tools_csv}}.
    Returns an empty string when path is None.
    """
    if path is None:
        return ""

    prefix_text = Path(path).read_text(encoding="utf-8")

    role = getattr(task, "role", "")

    # permitted tools = allowed_tools on the task (or empty)
    allowed = getattr(task, "allowed_tools", None) or []
    permitted_csv = ", ".join(allowed) if allowed else ""

    # forbidden tools = hard_fail_conditions on the task (or empty)
    hard_fail = getattr(task, "hard_fail_conditions", None) or []
    forbidden_csv = ", ".join(hard_fail) if hard_fail else ""

    prefix_text = prefix_text.replace("{{role}}", str(role))
    prefix_text = prefix_text.replace("{{permitted_tools_csv}}", permitted_csv)
    prefix_text = prefix_text.replace("{{forbidden_tools_csv}}", forbidden_csv)

    return prefix_text


def _build_adapter(name: str):
    """Instantiate an adapter by name using the prefix registry."""
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter
    from exabench.adapters.openai_adapter import OpenAIAdapter
    from exabench.adapters.mcp_client_adapter import MCPClientAdapter

    def _make_direct_qa(_n: str):
        return DirectQAAdapter()

    def _make_openai(n: str):
        model = n.split(":", 1)[1] if ":" in n else "gpt-4o"
        return OpenAIAdapter(model=model)

    def _make_anthropic(n: str):
        from exabench.adapters.anthropic_adapter import AnthropicAdapter
        model = n.split(":", 1)[1] if ":" in n else "claude-sonnet-4-6"
        return AnthropicAdapter(model=model)

    def _make_mcp(n: str):
        # "mcp:stdio:python server.py" → server_spec = "stdio:python server.py"
        # "mcp:sse:http://..."         → server_spec = "sse:http://..."
        server_spec = n[len("mcp:"):] if ":" in n else ""
        return MCPClientAdapter(server=server_spec)

    _REGISTRY = {
        "direct_qa": _make_direct_qa,
        "openai": _make_openai,
        "anthropic": _make_anthropic,
        "mcp": _make_mcp,
    }

    prefix = name.split(":")[0]
    factory = _REGISTRY.get(prefix)
    if factory is None:
        known = ", ".join(_REGISTRY)
        raise ValueError(f"Unknown adapter {name!r}. Known prefixes: {known}")
    return factory(name)


def _build_exporter(langfuse: bool):
    """Instantiate a LangfuseExporter when --langfuse is set, else return None."""
    if not langfuse:
        return None
    from exabench.exporters.langfuse_exporter import LangfuseExporter
    try:
        return LangfuseExporter()
    except (ImportError, ValueError) as exc:
        typer.echo(f"Langfuse error: {exc}", err=True)
        raise typer.Exit(1)


def _generate_reports(run_dir: Path) -> None:
    from exabench.reports.html_report import write_html_report
    from exabench.reports.json_report import write_run_summary
    from exabench.reports.slices import format_table_text, role_category_table
    from exabench.reports.json_report import build_run_summary

    json_path = write_run_summary(str(run_dir))
    typer.echo(f"  JSON report : {json_path}")
    html_path = write_html_report(str(run_dir))
    typer.echo(f"  HTML report : {html_path}")
    summary = build_run_summary(str(run_dir))
    table = role_category_table(summary)
    typer.echo(f"\nRole × Category scores  (run: {summary['run_id']})\n")
    typer.echo(format_table_text(table))


def _check_fidelity_gate(env_id: str, fidelity_root: str = "data/fidelity") -> None:
    """Informational V0 fidelity gate check.

    Reads data/fidelity/index.json and warns if the environment's fidelity
    report failed. Does not hard-fail — the gate is informational in V0.
    If index.json is missing, silently skips the check.
    """
    index_path = Path(fidelity_root) / "index.json"
    if not index_path.exists():
        return

    try:
        import json

        entries = json.loads(index_path.read_text())
        for entry in entries:
            if entry.get("env_id") == env_id:
                if not entry.get("passed", True):
                    typer.echo(
                        f"[fidelity-gate] WARNING: environment '{env_id}' did not pass "
                        f"fidelity validation (see data/fidelity/{env_id}.md). "
                        "Continuing anyway (V0 gate is informational).",
                        err=True,
                    )
                return
    except Exception:  # noqa: BLE001
        pass  # Never block the run due to a fidelity-check error


def _load_split_ids(split: str, benchmark_root: str) -> set[str] | None:
    """Return the set of task IDs for the requested split, or None (= all tasks).

    Raises typer.Exit with an error message for the 'test' split (locked).
    """
    if split == "all":
        return None

    import sys
    sys.path.insert(0, str(Path(benchmark_root).parent))
    try:
        from benchmark.tasks.dataset_splits import (
            TEST_TASK_IDS, LITE_TASK_IDS, get_split
        )
        from exabench.loaders.task_loader import load_tasks_from_dir
    except ImportError:
        typer.echo("Could not import dataset_splits. Run from the repo root.", err=True)
        raise typer.Exit(1)
    finally:
        sys.path.pop(0)

    if split == "test":
        if not _os.environ.get("EXABENCH_UNLOCK_TEST"):
            typer.echo(
                "Error: Test split is locked. Set EXABENCH_UNLOCK_TEST=1 to unlock "
                "(one-shot only — results must not be used to inform further tuning).",
                err=True,
            )
            raise typer.Exit(1)
        ids = set(TEST_TASK_IDS)
        return ids

    if split == "lite":
        ids = set(LITE_TASK_IDS)
        if not ids:
            typer.echo(
                "Warning: LITE_TASK_IDS is empty. "
                "Run `exabench lite select` first to populate the Lite manifest.",
                err=True,
            )
        return ids

    if split == "dev":
        specs_dir = Path(benchmark_root) / "tasks" / "specs"
        all_ids = {t.task_id for t in load_tasks_from_dir(specs_dir)}
        return all_ids - set(TEST_TASK_IDS)

    typer.echo(f"Unknown split '{split}'. Use: all | dev | lite | test", err=True)
    raise typer.Exit(1)


def _run_all_for_model(
    *,
    adapter_label: str,
    adapter_obj,
    tasks: list,
    benchmark_root: str,
    output_root: str,
    split: str,
    langfuse: bool,
    report: bool,
    system_prompt_prefix_path: str | None,
) -> None:
    """Inner helper: run all tasks for one adapter/model and write artifacts."""
    from exabench.runners.runner import BenchmarkRunner
    from exabench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts
    from exabench.utils.ids import make_run_id
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

    exporter = _build_exporter(langfuse)
    run_id = make_run_id()
    runner = BenchmarkRunner(
        adapter=adapter_obj,
        benchmark_root=Path(benchmark_root),
        output_root=Path(output_root),
        exporter=exporter,
    )

    run_dir = Path(output_root) / run_id
    write_run_manifest(
        run_dir,
        model=adapter_label.split(":", 1)[1] if ":" in adapter_label else adapter_label,
        adapter=adapter_label,
        split=split,
    )

    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("{task.fields[status]}"),
        transient=False,
    ) as progress:
        task_bar = progress.add_task(
            f"run_id={run_id}  adapter={adapter_label}",
            total=len(tasks),
            status=f"0/{len(tasks)} done",
        )
        for bench_task in tasks:
            progress.update(task_bar, description=f"[bold blue]{bench_task.task_id}[/bold blue]")
            _check_fidelity_gate(bench_task.environment_id)

            # Apply system-prompt prefix if requested
            if system_prompt_prefix_path is not None:
                prefix = _load_system_prompt_prefix(system_prompt_prefix_path, bench_task)
                if hasattr(adapter_obj, "_system_prompt") and prefix:
                    original = adapter_obj._system_prompt
                    adapter_obj._system_prompt = prefix + "\n\n" + original

            try:
                result = runner.run(
                    bench_task.task_id,
                    bench_task.environment_id,
                    run_id=run_id,
                )
                results.append((bench_task.task_id, result))
                score_str = f"[green]score={result.aggregate_score:.4f}[/green]"
            except Exception as e:
                results.append((bench_task.task_id, None))
                score_str = f"[red]FAILED: {e}[/red]"
            finally:
                # Restore original system prompt
                if system_prompt_prefix_path is not None and hasattr(adapter_obj, "_system_prompt"):
                    adapter_obj._system_prompt = original  # type: ignore[possibly-undefined]

            succeeded = sum(1 for _, r in results if r is not None)
            progress.update(
                task_bar,
                advance=1,
                status=f"{succeeded}/{len(tasks)} done  last={score_str}",
            )

    finalize_run_artifacts(run_dir, results)

    typer.echo(f"\nRun ID: {run_id}  (adapter={adapter_label})")
    succeeded = sum(1 for _, r in results if r is not None)
    typer.echo(f"Completed: {succeeded}/{len(tasks)} tasks")

    if exporter:
        exporter.flush()

    if report:
        typer.echo("\nGenerating reports...")
        _generate_reports(run_dir)


@run_app.command("all")
def run_all(
    adapter: Annotated[str, typer.Option("--adapter", "-a", help="Adapter name (single-model, legacy)")] = "direct_qa",
    models: Annotated[str, typer.Option("--models", "-m", help="Comma-separated model tokens (e.g. direct_qa,gpt-4o)")] = "",
    benchmark_root: Annotated[str, typer.Option("--benchmark", help="Path to benchmark/")] = "benchmark",
    output_root: Annotated[str, typer.Option("--output", "-o", help="Output directory for runs")] = "data/runs",
    split: Annotated[str, typer.Option("--split", "-s", help="Task split: all | dev | lite | test")] = "all",
    report: Annotated[bool, typer.Option("--report/--no-report", help="Auto-generate JSON + HTML reports after run")] = True,
    langfuse: Annotated[bool, typer.Option("--langfuse/--no-langfuse", help="Export traces and scores to Langfuse")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable DEBUG logging")] = False,
    system_prompt_prefix: Annotated[Optional[str], typer.Option("--system-prompt-prefix", help="Path to a text file prepended to the agent system prompt")] = None,
) -> None:
    """Run all benchmark tasks. Uses each task's environment_id from its spec.

    Creates one run directory with traces and results for every task.
    Use --split lite|dev|all to filter which tasks are run.
    Use --models to run against multiple models in one invocation (each gets its own run dir).
    """
    configure_logging("DEBUG" if verbose else "WARNING")

    from exabench.loaders.task_loader import load_tasks_from_dir

    # Determine which model tokens to iterate over.
    # --models takes precedence over --adapter when provided.
    if models:
        model_tokens = [t.strip() for t in models.split(",") if t.strip()]
    else:
        # Legacy single-adapter path: validate with _build_adapter
        try:
            _build_adapter(adapter)
        except ValueError:
            typer.echo(
                f"Unknown adapter '{adapter}'. "
                "Available: direct_qa, openai, openai:gpt-4o, mcp:stdio:CMD, mcp:sse:URL",
                err=True,
            )
            raise typer.Exit(1)
        model_tokens = None  # signal: use legacy adapter path

    specs_dir = Path(benchmark_root) / "tasks" / "specs"
    all_tasks = load_tasks_from_dir(specs_dir)
    if not all_tasks:
        typer.echo(f"No tasks found in {specs_dir}", err=True)
        raise typer.Exit(1)

    split_ids = _load_split_ids(split, benchmark_root)
    if split_ids is not None:
        tasks = [t for t in all_tasks if t.task_id in split_ids]
        typer.echo(f"Split '{split}': {len(tasks)}/{len(all_tasks)} tasks selected.")
    else:
        tasks = all_tasks
    if not tasks:
        typer.echo(f"No tasks match split '{split}'.", err=True)
        raise typer.Exit(1)

    if model_tokens is not None:
        # Multi-model path: iterate over tokens
        for token in model_tokens:
            adapter_class, model_name = resolve_model(token)  # exits on unknown token
            if adapter_class.__name__ == "DirectQAAdapter":
                adapter_obj = adapter_class()
            else:
                adapter_obj = adapter_class(model=model_name)
            token_output = str(Path(output_root) / token)
            typer.echo(f"\n=== Model: {token} → output: {token_output} ===")
            _run_all_for_model(
                adapter_label=token,
                adapter_obj=adapter_obj,
                tasks=tasks,
                benchmark_root=benchmark_root,
                output_root=token_output,
                split=split,
                langfuse=langfuse,
                report=report,
                system_prompt_prefix_path=system_prompt_prefix,
            )
    else:
        # Legacy single-adapter path
        adapter_obj = _build_adapter(adapter)
        _run_all_for_model(
            adapter_label=adapter,
            adapter_obj=adapter_obj,
            tasks=tasks,
            benchmark_root=benchmark_root,
            output_root=output_root,
            split=split,
            langfuse=langfuse,
            report=report,
            system_prompt_prefix_path=system_prompt_prefix,
        )


@run_app.command("task")
def run_task(
    task_id: Annotated[str, typer.Option("--task", "-t", help="Task ID, e.g. JOB_USR_001")],
    env_id: Annotated[str, typer.Option("--env", "-e", help="Environment ID, e.g. env_01")],
    adapter: Annotated[str, typer.Option("--adapter", "-a", help="Adapter name")] = "direct_qa",
    benchmark_root: Annotated[str, typer.Option("--benchmark", help="Path to benchmark/")] = "benchmark",
    output_root: Annotated[str, typer.Option("--output", "-o", help="Output directory for runs")] = "data/runs",
    report: Annotated[bool, typer.Option("--report/--no-report", help="Auto-generate JSON + HTML reports after run")] = True,
    langfuse: Annotated[bool, typer.Option("--langfuse/--no-langfuse", help="Export traces and scores to Langfuse")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable DEBUG logging")] = False,
    system_prompt_prefix: Annotated[Optional[str], typer.Option("--system-prompt-prefix", help="Path to a text file prepended to the agent system prompt")] = None,
) -> None:
    """Run a single benchmark task."""
    configure_logging("DEBUG" if verbose else "WARNING")

    from exabench.loaders.task_loader import load_task
    from exabench.runners.runner import BenchmarkRunner

    try:
        adapter_obj = _build_adapter(adapter)
    except ValueError:
        typer.echo(
            f"Unknown adapter '{adapter}'. "
            "Available: direct_qa, openai, openai:gpt-4o, mcp:stdio:CMD, mcp:sse:URL",
            err=True,
        )
        raise typer.Exit(1)

    # Apply system-prompt prefix if provided
    if system_prompt_prefix is not None and hasattr(adapter_obj, "_system_prompt"):
        task_spec = load_task(Path(benchmark_root) / "tasks" / "specs" / f"{task_id}.json")
        prefix = _load_system_prompt_prefix(system_prompt_prefix, task_spec)
        if prefix:
            adapter_obj._system_prompt = prefix + "\n\n" + adapter_obj._system_prompt

    exporter = _build_exporter(langfuse)
    runner = BenchmarkRunner(
        adapter=adapter_obj,
        benchmark_root=Path(benchmark_root),
        output_root=Path(output_root),
        exporter=exporter,
    )

    from exabench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts
    from exabench.utils.ids import make_run_id

    single_run_id = make_run_id()
    single_run_dir = Path(output_root) / single_run_id
    write_run_manifest(
        single_run_dir,
        model=adapter.split(":", 1)[1] if ":" in adapter else adapter,
        adapter=adapter,
        split="single",
    )

    _check_fidelity_gate(env_id)
    typer.echo(f"Running task={task_id}  env={env_id}  adapter={adapter}")
    result = runner.run(task_id, env_id, run_id=single_run_id)

    finalize_run_artifacts(single_run_dir, [result])

    if exporter:
        exporter.flush()

    typer.echo(f"\nResult: aggregate_score={result.aggregate_score:.4f}  hard_fail={result.hard_fail}")
    d = result.dimension_scores
    typer.echo(f"  outcome={d.outcome}  tool_use={d.tool_use}  "
               f"governance={d.governance}  efficiency={d.efficiency}")
    typer.echo(f"\nRun ID: {result.run_id}")

    if report:
        run_dir = Path(output_root) / result.run_id
        typer.echo("\nGenerating reports...")
        _generate_reports(run_dir)
