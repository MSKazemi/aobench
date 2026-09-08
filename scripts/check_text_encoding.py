#!/usr/bin/env python3
"""Fail when text I/O omits an explicit encoding.

Python's text mode defaults to ``locale.getpreferredencoding()``. On Linux and
macOS that is UTF-8, so a missing ``encoding=`` is invisible in CI. On Windows it
is cp1252, and every one of these calls raises ``UnicodeEncodeError`` on the
first non-ASCII byte.

That is not hypothetical. A contributor benchmarking a model on Windows lost a
run at task 6 of 67 because ``TraceWriter`` wrote agent output containing an
emoji through an encoding-less ``write_text``. The read path was equally exposed:
the corpus itself contains em-dashes and other non-ASCII text, so loading task
specs, environment docs and RBAC policy would have failed the same way.

Unlike the silent-handler ratchet, this is a clean-tree gate: there is no
legitimate reason to open a text file without saying what encoding it is in, so
the accepted count is zero. Binary mode (``"rb"``/``"wb"``) is exempt, because
encoding does not apply.

Usage::

    python scripts/check_text_encoding.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "aobench"

#: Calls that open a file and therefore take an ``encoding`` in text mode.
_OPENERS = {"open", "read_text", "write_text"}


def _is_binary_mode(call: ast.Call, name: str) -> bool:
    """True when an explicit binary mode makes ``encoding`` inapplicable.

    The mode is the first positional argument of ``Path.open(mode)`` but the
    second of the builtin ``open(file, mode)``.
    """
    positional = call.args[1:] if name == "open" and _is_builtin_open(call) else call.args
    for arg in positional:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "b" in arg.value:
            return True
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str) and "b" in kw.value.value:
                return True
    return False


def _is_builtin_open(call: ast.Call) -> bool:
    """Distinguish the builtin ``open(file, mode)`` from ``path.open(mode)``."""
    return isinstance(call.func, ast.Name)


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def find_violations(root: Path) -> list[tuple[str, int, str]]:
    found: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name not in _OPENERS:
                continue
            if any(kw.arg == "encoding" for kw in node.keywords):
                continue
            if _is_binary_mode(node, name):
                continue
            found.append((str(path.relative_to(ROOT)), node.lineno, name))
    return found


def main() -> int:
    violations = find_violations(SRC)
    if not violations:
        print("check_text_encoding: OK — all text I/O declares an explicit encoding.")
        return 0

    print(f"check_text_encoding: {len(violations)} call(s) open text without an encoding.\n")
    for rel, line, name in violations:
        print(f"  {rel}:{line}: {name}() has no encoding= (cp1252 on Windows)")
    print('\nFix: pass encoding="utf-8" explicitly. Use binary mode if it is not text.')
    return 1


if __name__ == "__main__":
    sys.exit(main())
