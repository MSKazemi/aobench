#!/usr/bin/env python
"""Generate hpc_tools_guide.md in each environment's docs/ directory.

Writes one Markdown file per environment, filtered to the role declared in
that environment's metadata.yaml (or all roles if no single role is declared).

Usage:
    uv run python scripts/generate_tool_docs.py
    uv run python scripts/generate_tool_docs.py --benchmark benchmark --role sysadmin
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from the project root without installing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exabench.tools.catalog_loader import generate_docs_page, load_catalog

_DEFAULT_BENCHMARK = Path(__file__).parent.parent / "benchmark"
_ENV_DIR_NAME = "environments"
_DOCS_FILE = "hpc_tools_guide.md"

_ALL_ROLES = [
    "scientific_user",
    "researcher",
    "sysadmin",
    "facility_admin",
    "system_designer",
]


def _detect_role(env_dir: Path) -> str | None:
    """Try to read the primary role from metadata.yaml, return None if ambiguous."""
    metadata = env_dir / "metadata.yaml"
    if not metadata.exists():
        return None
    try:
        import yaml
        with metadata.open() as fh:
            meta = yaml.safe_load(fh)
        roles = meta.get("supported_roles", [])
        if isinstance(roles, list) and len(roles) == 1:
            return roles[0]
    except Exception:
        pass
    return None


def generate_all(benchmark: Path, forced_role: str | None, dry_run: bool) -> None:
    catalog = load_catalog()
    env_root = benchmark / _ENV_DIR_NAME

    if not env_root.exists():
        print(f"No environments directory found at {env_root}", file=sys.stderr)
        sys.exit(1)

    env_dirs = sorted(d for d in env_root.iterdir() if d.is_dir())
    if not env_dirs:
        print(f"No environment directories found in {env_root}", file=sys.stderr)
        sys.exit(1)

    written = 0
    for env_dir in env_dirs:
        role = forced_role or _detect_role(env_dir) or "sysadmin"
        docs_dir = env_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        out_path = docs_dir / _DOCS_FILE
        md = generate_docs_page(catalog, role=role)
        if dry_run:
            print(f"[dry-run] would write {out_path} (role={role}, {len(md)} chars)")
        else:
            out_path.write_text(md, encoding="utf-8")
            print(f"  wrote {out_path} (role={role})")
        written += 1

    print(f"\n{'[dry-run] ' if dry_run else ''}Done — {written} environment(s) processed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--benchmark", default=str(_DEFAULT_BENCHMARK), help="Path to benchmark directory")
    parser.add_argument("--role", default=None, choices=_ALL_ROLES, help="Force a specific role for all envs")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be written without writing")
    args = parser.parse_args()

    generate_all(
        benchmark=Path(args.benchmark),
        forced_role=args.role,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
