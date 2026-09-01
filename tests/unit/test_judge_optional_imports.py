"""The judge runner must import without the optional ``openai`` extra.

``openai`` is declared as an optional extra in ``pyproject.toml`` and is imported
lazily inside :meth:`JudgeRunner._try_openai`. A module-level import of anything
under ``openai`` — including a types-only symbol used purely for annotations —
breaks ``import aobench.judge.runner`` on a base install.

The development environment installs the extra, so an ordinary import test cannot
catch this; the finder below simulates the extra being absent.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest


class _BlockOpenAI:
    """Meta-path finder that makes ``openai`` look uninstalled."""

    def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
        if fullname == "openai" or fullname.startswith("openai."):
            raise ImportError(f"No module named {fullname!r} (simulated: extra not installed)")
        return None


@pytest.fixture
def without_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys, "meta_path", [_BlockOpenAI(), *sys.meta_path], raising=False
    )
    for name in [m for m in sys.modules if m == "openai" or m.startswith("openai.")]:
        monkeypatch.delitem(sys.modules, name, raising=False)
    for name in [m for m in sys.modules if m.startswith("aobench.judge")]:
        monkeypatch.delitem(sys.modules, name, raising=False)


def test_judge_runner_imports_without_openai(without_openai: None) -> None:
    module = importlib.import_module("aobench.judge.runner")
    assert isinstance(module, ModuleType)
    assert hasattr(module, "JudgeRunner")
