"""Entry point for make repro-* targets.

Usage (via Makefile):
  make repro-table-1
  make repro-table-2
  make repro-determinism
  make fetch-snapshots
"""

from __future__ import annotations

import typer

app = typer.Typer(help="ExaBench reproducibility targets.")


@app.command("table-1")
def table_1() -> None:
    """Reproduce Table 1 (main results) from locked run artifacts."""
    typer.echo("repro-table-1: not yet run")


@app.command("table-2")
def table_2() -> None:
    """Reproduce Table 2 from locked run artifacts."""
    typer.echo("repro-table-2: not yet run")


@app.command("determinism")
def determinism() -> None:
    """Verify replay determinism for all benchmark environment snapshots (§11)."""
    from pathlib import Path
    from exabench.environment.replay_determinism import verify_replay_determinism

    env_base = Path("benchmark/environments")
    if not env_base.exists():
        typer.echo("No benchmark/environments/ directory found.")
        raise typer.Exit(code=1)

    env_dirs = sorted(d for d in env_base.iterdir() if d.is_dir())
    if not env_dirs:
        typer.echo("No environment directories found.")
        raise typer.Exit(code=0)

    all_passed = True
    for env_dir in env_dirs:
        report = verify_replay_determinism(env_dir)
        status = "PASS" if report.passed else "FAIL"
        typer.echo(f"  {env_dir.name:20} {status}")
        for h in report.hash_results:
            if h["status"] not in ("recorded", "missing", "no_fixture"):
                icon = "✓" if h["passed"] else "✗"
                typer.echo(f"    {icon} {h['file']}")
        for c in report.cadence_results:
            if not c.passed:
                typer.echo(f"    ✗ cadence {c.stream}: {c.message}")
        if not report.passed:
            all_passed = False

    if all_passed:
        typer.echo("\nAll environments passed determinism check.")
    else:
        typer.echo("\nSome environments FAILED determinism check.")
        raise typer.Exit(code=1)


@app.command("fetch-snapshots")
def fetch_snapshots() -> None:
    """Download canonical snapshot bundles from the remote artifact store."""
    typer.echo("fetch-snapshots: not yet run")


if __name__ == "__main__":
    app()
