"""T6 checker: Environment freeze.

Performs static analysis of all tool source files under
``src/aobench/tools/`` to detect patterns that indicate live network
calls, real-time clock reads, or other non-deterministic I/O that would
break environment reproducibility.

Flagged patterns (from spec §5.6):
- ``requests.get``
- ``urllib``
- ``httpx``
- ``socket.connect``
- ``subprocess(["curl"``
- ``datetime.now()``
- ``time.time()``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from aobench.cli.validators.base import CheckResult

# Patterns that indicate non-deterministic / live I/O
_LIVE_PATTERNS: list[tuple[str, str]] = [
    (r"\brequests\.get\b", "requests.get (live HTTP call)"),
    (r"\burllib\b", "urllib (live HTTP call)"),
    (r"\bhttpx\b", "httpx (live HTTP call)"),
    (r"\bsocket\.connect\b", "socket.connect (live TCP connection)"),
    (r'subprocess\(\["curl"', 'subprocess(["curl"...) (live HTTP via shell)'),
    (r"\bdatetime\.now\(\)", "datetime.now() (real-time clock)"),
    (r"\btime\.time\(\)", "time.time() (real-time clock)"),
]

_COMPILED_PATTERNS = [(re.compile(pat), desc) for pat, desc in _LIVE_PATTERNS]


def check_environment_freeze(snapshot_dir: str | Path) -> CheckResult:
    """Scan tool source files for live/non-deterministic I/O patterns.

    Parameters
    ----------
    snapshot_dir:
        The root environments directory.  This parameter is accepted for
        interface consistency but the check targets the tool source tree,
        not the snapshot contents.

    Returns
    -------
    CheckResult
        PASS — no live I/O patterns found in tool source files.
        WARN — patterns found in non-critical locations (comments/strings).
        FAIL — live I/O patterns found in executable tool code.
        SKIP — tool source directory not found.
    """
    # Locate the tools source directory relative to this file
    tools_dir = Path(__file__).parent.parent.parent / "tools"

    if not tools_dir.exists():
        return CheckResult(
            status="SKIP",
            detail=f"Tools source directory not found at '{tools_dir}'; skipping env-freeze check.",
        )

    violations: list[str] = []
    scanned = 0

    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("__"):
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue

        scanned += 1
        file_violations = _scan_source(py_file, source)
        violations.extend(file_violations)

    if scanned == 0:
        return CheckResult(
            status="SKIP",
            detail="No tool source files found to scan.",
        )

    if violations:
        return CheckResult(
            status="FAIL",
            detail=(
                f"Environment-freeze violations found in tool source "
                f"({len(violations)} issue(s)): {violations[:5]}"
                + (" ..." if len(violations) > 5 else "")
            ),
            fix_suggestion=(
                "Replace live I/O calls with snapshot-backed equivalents.  "
                "Use pre-loaded JSON/YAML data from the environment directory "
                "instead of making network calls or reading the system clock.  "
                "For datetime, inject a fixed timestamp from the snapshot metadata."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=(
            f"No live I/O patterns detected in {scanned} tool source file(s). "
            "Environment appears fully frozen/reproducible."
        ),
    )


def _scan_source(py_file: Path, source: str) -> list[str]:
    """Return list of violation descriptions for a single source file."""
    violations: list[str] = []

    for line_no, line in enumerate(source.splitlines(), start=1):
        # Skip comment lines
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        for pattern, description in _COMPILED_PATTERNS:
            if pattern.search(line):
                violations.append(
                    f"{py_file.name}:{line_no}: {description}"
                )
                break  # one match per line is enough

    return violations
