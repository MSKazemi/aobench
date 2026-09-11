"""AOBench CLI entry point."""

# ruff: noqa: E402  (load_dotenv must run before sub-commands read env vars at import time)

import typer
from dotenv import load_dotenv

load_dotenv()

from aobench import __version__
from aobench.cli.clear_cmd import clear_app
from aobench.cli.rbac_cmd import rbac_app
from aobench.cli.compare_cmd import compare_app
from aobench.cli.info_cmd import doctor as doctor_cmd, info as info_cmd
from aobench.cli.leaderboard_cmd import leaderboard_app
from aobench.cli.list_cmd import list_app
from aobench.cli.new_cmd import new_app
from aobench.cli.lite_cmd import lite_app
from aobench.cli.quickstart_cmd import quickstart_app
from aobench.cli.report_cmd import report_app
from aobench.cli.rescore_cmd import rescore as rescore_cmd
from aobench.cli.robustness_cmd import robustness_app
from aobench.cli.run_cmd import run_app
from aobench.cli.serve_cmd import serve_app
from aobench.cli.validate_cmd import validate_app

_EPILOG = """
New here? Run `aobench quickstart` — one command, no API key, no cluster.

`aobench doctor` checks the install. `aobench list tasks` browses the corpus.

`aobench list adapters` shows what you can evaluate, and what each one needs.

Docs: https://mskazemi.com/aobench/ — Issues: https://github.com/MSKazemi/aobench/issues
"""

app = typer.Typer(
    name="aobench",
    help=(
        "AOBench — the open-source benchmark for AI agents that operate HPC systems. "
        "Role-aware, permission-enforced, trace-scored, and reproducible without a cluster."
    ),
    epilog=_EPILOG,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"aobench {__version__}")
        raise typer.Exit


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Print the AOBench version and exit.",
    ),
) -> None:
    """AOBench root command — see the sub-commands below."""


app.add_typer(run_app, name="run")
app.add_typer(validate_app, name="validate")
app.add_typer(list_app, name="list")
app.add_typer(lite_app, name="lite")
app.add_typer(report_app, name="report")
app.add_typer(compare_app, name="compare")
app.command(name="rescore")(rescore_cmd)
app.add_typer(robustness_app, name="robustness")
app.add_typer(clear_app, name="clear")
app.add_typer(leaderboard_app, name="leaderboard")
app.add_typer(rbac_app, name="rbac")
app.add_typer(serve_app, name="serve")
app.add_typer(quickstart_app, name="quickstart")
app.add_typer(new_app, name="new")
app.command(name="info")(info_cmd)
app.command(name="doctor")(doctor_cmd)


if __name__ == "__main__":
    app()
