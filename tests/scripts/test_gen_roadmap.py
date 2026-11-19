"""Offline tests for scripts/gen_roadmap.py — no network, fixture data only."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gen_roadmap", ROOT / "scripts" / "gen_roadmap.py")
assert _spec and _spec.loader
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

FACTS = json.loads((ROOT / "benchmark" / "BENCHMARK_FACTS.json").read_text(encoding="utf-8"))
T0 = dt.datetime(2026, 11, 19, 20, 0, tzinfo=dt.timezone.utc)
T1 = dt.datetime(2026, 11, 26, 6, 0, tzinfo=dt.timezone.utc)


def _issue(n: int, title: str, milestone: str | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "number": n,
        "title": title,
        "html_url": f"https://github.com/MSKazemi/aobench/issues/{n}",
        "milestone": {"title": milestone} if milestone else None,
        "labels": extra.pop("labels", []),
        **extra,
    }


def _data() -> dict[str, Any]:
    return {
        "repo": "MSKazemi/aobench",
        "milestones": [
            {
                "title": "v0.5 — Contributor on-ramp & DX",
                "html_url": "https://github.com/MSKazemi/aobench/milestone/1",
                "open_issues": 1,
                "closed_issues": 16,
                "due_on": None,
            }
        ],
        "issues": [
            _issue(72, "Flaky release gate", "v0.5 — Contributor on-ramp & DX"),
            _issue(97, "[HF-01][P0] Audit release eligibility"),
            _issue(
                96, "[EPIC][HF] Hub integration", sub_issues_summary={"total": 14, "completed": 0}
            ),
            _issue(113, "New docs issue", labels=[{"name": "priority:P2"}]),
        ],
        "latest_release": {
            "tag_name": "v0.4.1",
            "html_url": "https://github.com/MSKazemi/aobench/releases/tag/v0.4.1",
            "published_at": "2026-08-08T20:43:12Z",
        },
    }


def _doc(block: str = "") -> str:
    return (
        "# AOBench Roadmap\n\n<!--roadmap-start-->\n"
        f"{gen.START}\nold\n{gen.END}\n\n## Shipped\n\nhand-written\n<!--roadmap-end-->\n"
    )


def test_render_uses_generated_facts_and_release() -> None:
    out = gen.render(_data(), FACTS, "2026-11-19 20:00")
    assert f"{FACTS['tasks_total']} tasks ({FACTS['tasks_dev']} dev / {FACTS['tasks_test']}" in out
    assert "[v0.4.1](https://github.com/MSKazemi/aobench/releases/tag/v0.4.1) (2026-08-08)" in out
    assert "_Last updated (UTC): 2026-11-19 20:00_" in out
    assert out.startswith(gen.START) and out.endswith(gen.END)


def test_render_groups_by_milestone() -> None:
    out = gen.render(_data(), FACTS, "x")
    assert "16 of 17 closed · no due date." in out
    assert "| [#72](https://github.com/MSKazemi/aobench/issues/72) | Flaky release gate |" in out
    assert "### Not yet in a milestone" in out
    assert "| 0 / 14 |" in out  # epic sub-issue progress


def test_render_is_deterministic_regardless_of_input_order() -> None:
    a, b = _data(), _data()
    b["issues"].reverse()
    assert gen.render(a, FACTS, "x") == gen.render(b, FACTS, "x")


def test_update_preserves_hand_written_text() -> None:
    new = gen.update(_doc(), _data(), FACTS, T0)
    assert "## Shipped\n\nhand-written\n<!--roadmap-end-->" in new
    assert "\nold\n" not in new


def test_stamp_moves_only_when_content_changes() -> None:
    first = gen.update(_doc(), _data(), FACTS, T0)
    # Same data a week later: byte-identical, old stamp kept.
    assert gen.update(first, _data(), FACTS, T1) == first
    # Changed data a week later: new content and new stamp.
    changed = _data()
    changed["issues"].append(_issue(120, "Something new"))
    second = gen.update(first, changed, FACTS, T1)
    assert "_Last updated (UTC): 2026-11-26 06:00_" in second
    assert "Something new" in second


def test_missing_markers_fail_loudly() -> None:
    with pytest.raises(SystemExit, match="markers"):
        gen.splice("# no markers here\n", "block")


def test_pipe_in_title_is_escaped() -> None:
    data = _data()
    data["issues"] = [_issue(5, "a | b")]
    assert "a \\| b" in gen.render(data, FACTS, "x")
