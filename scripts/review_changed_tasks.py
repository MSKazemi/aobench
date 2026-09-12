#!/usr/bin/env python3
"""Run ``aobench review task`` over the task specs a branch changed.

`aobench review task` answers "is this one task right?". This wraps it so the answer arrives
where a corpus pull request is actually decided: in CI, as a rendered checklist, before a
human opens the diff.

That matters because reviewing corpus PRs is the thing that caps this project at one
maintainer. Most of the published review checklist is mechanical — does the evidence exist,
are the tool families real, is this a near-duplicate — and every minute spent re-deriving
those by hand is a minute not spent on the half that needs an operator: whether the question
is real and whether the gold answer is right.

Run with no arguments it reviews whatever you changed against ``origin/main``, so a
contributor can see the same checklist locally before pushing:

    uv run python scripts/review_changed_tasks.py

It shells out to the CLI with ``--json`` rather than importing the checkers, deliberately:
that is the documented machine-readable interface, so if it ever breaks, this gate notices.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PREFIX = "benchmark/tasks/specs/"

# FAIL is mechanically invalid and TODO is objective scaffold text. WARN remains a human
# judgement call and must not gate a PR.
_BLOCKING = {"FAIL", "TODO"}

_ICON = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "TODO": "📝", "SKIP": "➖"}


class DiffFailed(RuntimeError):
    """The diff itself could not run.

    Raised rather than returning an empty list, because "no specs changed" and "I could not
    tell what changed" must not look the same to a gate. Swallowing this would turn a broken
    base ref into a silently passing review -- exactly the shape `check_silent_handlers.py`
    exists to prevent.
    """


def _changed_specs(base: str) -> list[str]:
    """Task spec paths added or modified relative to *base*."""
    try:
        out = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=d",
                f"{base}...HEAD",
                "--",
                f"{SPEC_PREFIX}*.json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise DiffFailed(f"could not diff against {base!r}: {exc.stderr.strip() or exc}") from exc
    return [line.strip() for line in out.splitlines() if line.strip()]


def _review(spec_path: str) -> dict[str, object] | None:
    """Return the parsed ``review task --json`` payload, or None if it could not run."""
    proc = subprocess.run(
        ["uv", "run", "aobench", "review", "task", spec_path, "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    stdout = proc.stdout.strip()
    if not stdout:
        print(f"{spec_path}: review produced no output\n{proc.stderr}", file=sys.stderr)
        return None
    try:
        # The command exits non-zero on FAIL, which is expected here: the payload is
        # still on stdout and is exactly what we want to render.
        return json.loads(stdout[stdout.index("{") :])
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"{spec_path}: could not parse review output ({exc})", file=sys.stderr)
        return None


def _render(reports: list[dict[str, object]]) -> str:
    """A GitHub-flavoured markdown checklist, one section per changed task."""
    lines = ["## Corpus review", ""]
    blocking = sum(1 for r in reports if r["_blocking"])
    if blocking:
        lines.append(f"**{blocking} of {len(reports)} changed task(s) have a blocking failure.**")
    else:
        lines.append(
            f"All {len(reports)} changed task(s) pass the mechanical checks. "
            "What is left needs a human."
        )
    lines.append("")

    for report in reports:
        checks = report["checks"]  # type: ignore[index]
        head = "❌" if report["_blocking"] else "✅"
        lines += [
            f"### {head} `{report.get('task_id')}`",
            "",
            "| | Check | Detail |",
            "|---|---|---|",
        ]
        for check in checks:  # type: ignore[union-attr]
            detail = str(check["detail"]).replace("|", "\\|")
            lines.append(f"| {_ICON.get(check['status'], '')} | {check['item']} | {detail} |")
        lines.append("")

    lines += [
        "---",
        "",
        "`FAIL` and scaffold `TODO` rows block. `WARN` rows are for the reviewer to judge.",
        "",
        "What this check **cannot** tell you, and what review is actually for:",
        "",
        "- Is this a question the role would really ask?",
        "- Is the gold answer right?",
        "",
        "Run the same checklist locally with `aobench review task <TASK_ID>`.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Spec paths to review (default: what changed).")
    parser.add_argument("--base", default="origin/main", help="Base ref to diff against.")
    parser.add_argument(
        "--from-file", help="Read newline-separated spec paths from this file instead."
    )
    args = parser.parse_args()

    if args.from_file:
        content = Path(args.from_file).read_text(encoding="utf-8")
        specs = [line.strip() for line in content.splitlines() if line.strip()]
    elif args.paths:
        specs = args.paths
    else:
        try:
            specs = _changed_specs(args.base)
        except DiffFailed as exc:
            print(
                f"{exc}\n\nThe review could not determine what changed, so it is failing"
                " rather than reporting a clean run.",
                file=sys.stderr,
            )
            return 2

    specs = [s for s in specs if s.startswith(SPEC_PREFIX) and s.endswith(".json")]
    if not specs:
        print("No task specs changed — nothing to review.")
        return 0

    reports = []
    for spec in specs:
        report = _review(spec)
        if report is None:
            return 2
        report["_blocking"] = any(c["status"] in _BLOCKING for c in report["checks"])
        reports.append(report)

    summary = _render(reports)
    print(summary)

    # The step summary renders on the run page, so a reviewer sees the checklist without
    # a bot comment -- which also means this works on a fork PR, where the token is
    # read-only and commenting is not possible.
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(summary + "\n")

    return 1 if any(r["_blocking"] for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
