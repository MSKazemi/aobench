"""Mock docs tool — keyword search over environment documentation files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from aobench.tools.base import BaseTool, ToolResult


class MockDocsTool(BaseTool):
    name = "docs"

    def __init__(self, env_root: str, role: str) -> None:
        super().__init__(env_root)
        self._role = role
        self._docs = self._load_docs()

    def _load_docs(self) -> dict[str, str]:
        docs_dir = Path(self._env_root) / "docs"
        result: dict[str, str] = {}
        if docs_dir.exists():
            for p in sorted(docs_dir.glob("*.md")):
                result[p.stem] = p.read_text(encoding="utf-8")
        return result

    def call(self, method: str, **kwargs: Any) -> ToolResult:
        dispatch: dict[str, Callable[..., ToolResult]] = {
            "retrieve": self._retrieve,
            "list_docs": self._list_docs,
        }
        if method not in dispatch:
            return self._error(f"Unknown docs method: '{method}'")
        return dispatch[method](**kwargs)

    def _retrieve(
        self, query: str, max_results: int = 3, snippet_chars: int = 500
    ) -> ToolResult:
        """Keyword search returning a snippet *centred on the match*.

        The snippet must contain the matched term. Returning a fixed head of the
        document instead means a policy clause late in a long file can be matched
        but never surfaced, so an agent cannot ground an answer it was scored on.
        Windows are snapped to line boundaries and the scan order is the sorted
        document order, so results stay deterministic across runs.
        """
        terms = [w for w in query.lower().split() if w]
        hits: list[dict[str, str]] = []
        for name, content in self._docs.items():
            lowered = content.lower()
            # Anchor on the most *selective* matched term, not the earliest one.
            # "patient data" must not centre on "data" simply because that word
            # also appears in the title; the rare term is what the query is about.
            # Selectivity order: rarest term first, then the longest, then the
            # earliest. Length breaks the tie between a stopword that happens to
            # occur once ("where") and the real subject of the query ("patient").
            matches = [
                (lowered.count(w), -len(w), lowered.find(w))
                for w in terms
                if w in lowered
            ]
            if not matches:
                continue
            *_, anchor = min(matches)
            hits.append(
                {
                    "doc_name": name,
                    "snippet": self._window(content, anchor, snippet_chars),
                }
            )
            if len(hits) >= max_results:
                break
        return self._ok(hits)

    @staticmethod
    def _window(content: str, match_pos: int, width: int) -> str:
        """Return up to *width* chars of *content* around *match_pos*."""
        if len(content) <= width:
            return content
        start = max(0, match_pos - width // 2)
        end = min(len(content), start + width)
        start = max(0, end - width)
        # Snap outward to line boundaries so a clause is never cut mid-sentence.
        nl = content.rfind("\n", 0, start)
        start = 0 if nl == -1 else nl + 1
        nl = content.find("\n", end)
        end = len(content) if nl == -1 else nl
        snippet = content[start:end]
        if start > 0:
            snippet = "… " + snippet
        if end < len(content):
            snippet = snippet + " …"
        return snippet

    def _list_docs(self) -> ToolResult:
        return self._ok(list(self._docs.keys()))
