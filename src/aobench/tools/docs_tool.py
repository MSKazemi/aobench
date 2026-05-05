"""Mock docs tool — keyword search over environment documentation files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
                result[p.stem] = p.read_text()
        return result

    def call(self, method: str, **kwargs: Any) -> ToolResult:
        dispatch = {
            "retrieve": self._retrieve,
            "list_docs": self._list_docs,
        }
        if method not in dispatch:
            return self._error(f"Unknown docs method: '{method}'")
        return dispatch[method](**kwargs)

    def _retrieve(self, query: str, max_results: int = 3) -> ToolResult:
        query_lower = query.lower()
        hits: list[dict[str, str]] = []
        for name, content in self._docs.items():
            if any(word in content.lower() for word in query_lower.split()):
                # Return the first 500 chars as a snippet
                hits.append({"doc_name": name, "snippet": content[:500]})
            if len(hits) >= max_results:
                break
        return self._ok(hits if hits else [])

    def _list_docs(self) -> ToolResult:
        return self._ok(list(self._docs.keys()))
