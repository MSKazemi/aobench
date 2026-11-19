#!/usr/bin/env python3
"""Regenerate the live status block in ROADMAP.md from GitHub and the generated facts.

The block between ``<!--roadmap-status-start-->`` and ``<!--roadmap-status-end-->`` is
owned by this script; everything else in ROADMAP.md stays hand-written.

Sources (read-only):
  * GitHub REST API — milestones, open issues (with sub-issue progress), latest release.
    Unauthenticated works for this public repo; ``GITHUB_TOKEN`` raises the rate limit.
  * ``benchmark/BENCHMARK_FACTS.json`` — corpus counts (generated; never hand-edited).

The "Last updated" stamp changes only when the rendered content changes, so a scheduled
run that finds nothing new leaves the file byte-identical.

Usage:
  uv run python scripts/gen_roadmap.py            # print the block
  uv run python scripts/gen_roadmap.py --write    # update ROADMAP.md in place
  uv run python scripts/gen_roadmap.py --check    # exit 1 if ROADMAP.md is stale
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO = "MSKazemi/aobench"
API = "https://api.github.com"
ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "ROADMAP.md"
FACTS = ROOT / "benchmark" / "BENCHMARK_FACTS.json"
START = "<!--roadmap-status-start-->"
END = "<!--roadmap-status-end-->"
STAMP_RE = re.compile(r"^_Last updated \(UTC\): [^_]*_\n", re.MULTILINE)


def _get(path: str) -> Any:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "aobench-roadmap-sync"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — fixed https host
                return json.loads(resp.read().decode("utf-8"))
        except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise  # transient errors get three tries; then fail loudly, never write
            time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def _get_all(path: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    sep = "&" if "?" in path else "?"
    while True:
        batch = _get(f"{path}{sep}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise RuntimeError(f"unexpected response for {path}: {type(batch).__name__}")
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def fetch(repo: str = REPO) -> dict[str, Any]:
    """Collect everything the renderer needs. The only function that touches the network."""
    milestones = _get_all(f"/repos/{repo}/milestones?state=open")
    issues = [i for i in _get_all(f"/repos/{repo}/issues?state=open") if "pull_request" not in i]
    releases = _get_all(f"/repos/{repo}/releases")
    published = [r for r in releases if not r.get("draft") and not r.get("prerelease")]
    latest = max(published, key=lambda r: r["published_at"]) if published else None
    data = {"repo": repo, "milestones": milestones, "issues": issues, "latest_release": latest}
    check_consistent(data)
    return data


def check_consistent(data: dict[str, Any]) -> None:
    """Refuse to render from an incomplete fetch.

    A token without ``issues: read`` gets an empty issue list (not an error) from the API,
    which would silently wipe every table. Milestone counters are the cross-check.
    """
    expected = sum(m["open_issues"] for m in data["milestones"])
    in_milestones = sum(1 for i in data["issues"] if i.get("milestone"))
    if in_milestones < expected:
        raise SystemExit(
            f"Incomplete fetch: milestones report {expected} open issues but only "
            f"{in_milestones} were returned. Does the token have issues: read?"
        )


def _issue_line(issue: dict[str, Any]) -> str:
    title = issue["title"].replace("|", "\\|")
    return f"| [#{issue['number']}]({issue['html_url']}) | {title} |"


def render(data: dict[str, Any], facts: dict[str, Any], stamp: str) -> str:
    """Pure function: same inputs → same Markdown. Tested offline."""
    repo = data["repo"]
    issues = sorted(data["issues"], key=lambda i: i["number"])
    lines = [START, "", "## Current status", "", f"_Last updated (UTC): {stamp}_", ""]

    rel = data.get("latest_release")
    if rel:
        lines.append(
            f"- **Latest release:** [{rel['tag_name']}]({rel['html_url']}) "
            f"({rel['published_at'][:10]})."
        )
    lines.append(
        f"- **Corpus on `main`** (generated `benchmark/BENCHMARK_FACTS.json`, package "
        f"version {facts['version']}): {facts['tasks_total']} tasks "
        f"({facts['tasks_dev']} dev / {facts['tasks_test']} held-out test), "
        f"{facts['environments_total']} environments, {len(facts['qcats'])} QCATs, "
        f"{len(facts['roles'])} roles, {facts['scoring_dimensions']} weighted scoring dimensions."
    )
    lines.append(
        f"- **Open issues:** {len(issues)} — "
        f"[all issues](https://github.com/{repo}/issues) · "
        f"[milestones](https://github.com/{repo}/milestones)."
    )
    lines.append("")

    epics = [i for i in issues if (i.get("sub_issues_summary") or {}).get("total")]
    if epics:
        lines += ["### Epics", "", "| Epic | Sub-issues done |", "|---|---|"]
        for e in epics:
            s = e["sub_issues_summary"]
            lines.append(
                f"| [#{e['number']}]({e['html_url']}) {e['title'].replace('|', '/')} "
                f"| {s.get('completed', 0)} / {s['total']} |"
            )
        lines.append("")

    by_ms: dict[str, list[dict[str, Any]]] = {}
    for i in issues:
        by_ms.setdefault((i.get("milestone") or {}).get("title") or "", []).append(i)

    for m in sorted(data["milestones"], key=lambda m: m["title"]):
        total = m["open_issues"] + m["closed_issues"]
        lines += [
            f"### [{m['title']}]({m['html_url']})",
            "",
            f"{m['closed_issues']} of {total} closed"
            + (f" · due {m['due_on'][:10]}" if m.get("due_on") else " · no due date")
            + ".",
            "",
        ]
        open_here = by_ms.get(m["title"], [])
        if open_here:
            lines += ["| Issue | Title |", "|---|---|"]
            lines += [_issue_line(i) for i in open_here]
            lines.append("")

    unscheduled = by_ms.get("", [])
    if unscheduled:
        lines += [
            "### Not yet in a milestone",
            "",
            "| Issue | Title |",
            "|---|---|",
            *[_issue_line(i) for i in unscheduled],
            "",
        ]

    lines += [
        "_Generated by `scripts/gen_roadmap.py` (weekly workflow `roadmap-sync`); "
        "edit the issues, not this block. Priorities live on the project board._",
        "",
        END,
    ]
    return "\n".join(lines)


def splice(document: str, block: str) -> str:
    if START not in document or END not in document:
        raise SystemExit(f"ROADMAP.md is missing the {START} / {END} markers")
    head, rest = document.split(START, 1)
    _, tail = rest.split(END, 1)
    return head + block + tail


def _without_stamp(text: str) -> str:
    return STAMP_RE.sub("", text)


def update(document: str, data: dict[str, Any], facts: dict[str, Any], now: dt.datetime) -> str:
    """Return the new document; keep the old stamp when nothing but the stamp would change."""
    stamp = now.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    candidate = splice(document, render(data, facts, stamp))
    if _without_stamp(candidate) == _without_stamp(document):
        return document
    return candidate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="update ROADMAP.md in place")
    mode.add_argument("--check", action="store_true", help="exit 1 if ROADMAP.md is stale")
    args = ap.parse_args(argv)

    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    document = ROADMAP.read_text(encoding="utf-8")
    new = update(document, fetch(), facts, dt.datetime.now(dt.timezone.utc))
    if args.check:
        if new != document:
            print(
                "ROADMAP.md status block is stale — run: uv run python scripts/gen_roadmap.py --write"
            )
            return 1
        print("ROADMAP.md status block is current")
        return 0
    if args.write:
        if new == document:
            print("ROADMAP.md unchanged")
        else:
            ROADMAP.write_text(new, encoding="utf-8")
            print("ROADMAP.md updated")
        return 0
    sys.stdout.write(new.split(START, 1)[1].split(END, 1)[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
