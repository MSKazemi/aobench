"""exabench validate — validate benchmark data files."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

validate_app = typer.Typer(help="Validate benchmark data.")


@validate_app.command("benchmark")
def validate_benchmark(
    benchmark_root: Annotated[str, typer.Option("--benchmark")] = "benchmark",
) -> None:
    """Validate all task specs and environment bundles."""
    from exabench.loaders.registry import BenchmarkRegistry

    root = Path(benchmark_root)
    typer.echo(f"Validating benchmark at {root.resolve()}")
    registry = BenchmarkRegistry(root)
    registry.load_all()
    typer.echo(f"  Tasks loaded:        {len(registry.task_ids)}")
    typer.echo(f"  Environments loaded: {len(registry.environment_ids)}")
    typer.echo("Validation passed.")
