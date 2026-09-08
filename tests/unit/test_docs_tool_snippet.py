"""Unit tests for MockDocsTool snippet windowing.

Regression cover for the defect reported in issue #26: ``_retrieve`` returned a
fixed head of each document, so a term matched late in a long file was never
surfaced and could not be used to ground an answer that was scored on it.
"""

from __future__ import annotations

from pathlib import Path

from aobench.tools.docs_tool import MockDocsTool

ENV_ROOT = str(Path(__file__).parent.parent.parent / "benchmark" / "environments" / "env_21")


def _snippet(tool: MockDocsTool, query: str, doc: str) -> str:
    result = tool.call("retrieve", query=query)
    assert result.success
    for hit in result.data or []:
        if hit["doc_name"] == doc:
            return str(hit["snippet"])
    raise AssertionError(f"{doc!r} not returned for query {query!r}")


def test_snippet_contains_a_late_matching_term():
    """The compliance clause sits past char 900 of a 1090-char policy file."""
    tool = MockDocsTool(ENV_ROOT, role="scientific_user")
    snippet = _snippet(tool, "immediate account suspension", "data_management_policy")
    assert "suspension" in snippet.lower()


def test_snippet_anchors_on_the_most_selective_term():
    """A stopword or title word must not pull the window away from the subject."""
    tool = MockDocsTool(ENV_ROOT, role="scientific_user")
    snippet = _snippet(tool, "where can patient data be stored", "data_management_policy")
    assert "patient" in snippet.lower()


def test_unrelated_query_still_returns_its_own_section():
    """Fixing the late-match case must not drag every query to the same window."""
    tool = MockDocsTool(ENV_ROOT, role="scientific_user")
    snippet = _snippet(tool, "retention", "data_management_policy")
    assert "retention" in snippet.lower()


def test_snippet_respects_the_width_budget():
    tool = MockDocsTool(ENV_ROOT, role="scientific_user")
    snippet = _snippet(tool, "PII", "data_management_policy")
    # Line-boundary snapping and the ellipsis markers add a small, bounded margin.
    assert len(snippet) <= 500 + 120


def test_retrieve_is_deterministic():
    """Same query, same snapshot, same bytes — the benchmark depends on it."""
    tool = MockDocsTool(ENV_ROOT, role="scientific_user")
    first = tool.call("retrieve", query="PII tier4_sensitive").data
    second = tool.call("retrieve", query="PII tier4_sensitive").data
    assert first == second


def test_no_match_returns_empty_list():
    tool = MockDocsTool(ENV_ROOT, role="scientific_user")
    result = tool.call("retrieve", query="zzzzznotpresentzzzzz")
    assert result.success
    assert result.data == []
