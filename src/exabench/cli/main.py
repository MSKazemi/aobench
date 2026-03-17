"""ExaBench CLI entry point."""

import typer

from exabench.cli.run_cmd import run_app
from exabench.cli.validate_cmd import validate_app

app = typer.Typer(
    name="exabench",
    help="ExaBench — benchmark framework for AI agents in HPC environments.",
    no_args_is_help=True,
)

app.add_typer(run_app, name="run")
app.add_typer(validate_app, name="validate")


if __name__ == "__main__":
    app()
