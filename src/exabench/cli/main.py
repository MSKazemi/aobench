"""ExaBench CLI entry point."""

import typer
from dotenv import load_dotenv

load_dotenv()  # load .env from the current working directory

from exabench.cli.clear_cmd import clear_app
from exabench.cli.compare_cmd import compare_app
from exabench.cli.leaderboard_cmd import leaderboard_app
from exabench.cli.lite_cmd import lite_app
from exabench.cli.report_cmd import report_app
from exabench.cli.rescore_cmd import app as rescore_app
from exabench.cli.robustness_cmd import robustness_app
from exabench.cli.run_cmd import run_app
from exabench.cli.validate_cmd import validate_app

app = typer.Typer(
    name="exabench",
    help="ExaBench — benchmark framework for evaluating AI agents in HPC environments.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.add_typer(run_app, name="run")
app.add_typer(validate_app, name="validate")
app.add_typer(lite_app, name="lite")
app.add_typer(report_app, name="report")
app.add_typer(compare_app, name="compare")
app.add_typer(rescore_app, name="rescore")
app.add_typer(robustness_app, name="robustness")
app.add_typer(clear_app, name="clear")
app.add_typer(leaderboard_app, name="leaderboard")


if __name__ == "__main__":
    app()
