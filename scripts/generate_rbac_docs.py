"""generate_rbac_docs.py — Generate docs/rbac_policy.md for every environment bundle.

Reads benchmark/environments/env_*/policy/rbac_policy.yaml (v1.1) and writes
a human-readable markdown document to benchmark/environments/env_*/docs/rbac_policy.md.

Usage:
    python3 scripts/generate_rbac_docs.py
    python3 scripts/generate_rbac_docs.py --env-base path/to/environments
    python3 scripts/generate_rbac_docs.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


DEFAULT_ENV_BASE = "benchmark/environments"


def _actions_str(actions: list[str]) -> str:
    if not actions:
        return "*(none)*"
    return ", ".join(f"`{a}`" for a in actions)


def _list_str(items: list[str]) -> str:
    if not items:
        return "*(none)*"
    return ", ".join(f"`{i}`" for i in items)


def _partitions_str(partitions: list[dict]) -> str:
    if not partitions:
        return "*(none)*"
    parts = []
    for p in partitions:
        name = p.get("name", "?")
        wt = p.get("max_walltime", "")
        if wt:
            parts.append(f"`{name}` (max {wt})")
        else:
            parts.append(f"`{name}`")
    return ", ".join(parts)


def render_rbac_markdown(env_id: str, policy: dict[str, Any]) -> str:
    """Render a RBAC policy YAML dict to a markdown string."""
    version = policy.get("version", "unknown")
    hard_fail = policy.get("hard_fail_on_violation", False)
    roles: dict[str, Any] = policy.get("roles", {})
    access_tiers: dict[str, Any] = policy.get("access_tiers", {})

    lines: list[str] = []

    lines.append(f"# RBAC Policy — {env_id}")
    lines.append("")
    lines.append(f"**Version:** {version}  ")
    lines.append(f"**Hard-fail on violation:** `{str(hard_fail).lower()}`")
    lines.append("")

    # ── Roles ──────────────────────────────────────────────────────────────
    lines.append("## Roles")
    lines.append("")

    for role_name, role_def in roles.items():
        description = role_def.get("description", "")
        permissions: list[dict] = role_def.get("permissions", [])
        allowed_tools: list[str] = role_def.get("allowed_tools", [])
        partition_access: list[dict] = role_def.get("partition_access", [])

        lines.append(f"### `{role_name}`")
        if description:
            lines.append(f"> {description}")
        lines.append("")

        if permissions:
            lines.append("**Permissions:**")
            lines.append("")
            lines.append("| Resource | Actions | Constraint |")
            lines.append("|----------|---------|------------|")
            for perm in permissions:
                resource = perm.get("resource", "?")
                acts = _actions_str(perm.get("actions", []))
                constraint = perm.get("constraint", "")
                lines.append(f"| `{resource}` | {acts} | {constraint} |")
            lines.append("")

        lines.append(f"**Allowed tools:** {_list_str(allowed_tools)}  ")
        lines.append(f"**Partition access:** {_partitions_str(partition_access)}")
        lines.append("")

    # ── Access Tiers ───────────────────────────────────────────────────────
    if access_tiers:
        lines.append("## Access Tiers")
        lines.append("")
        lines.append("| Tier | Resources | Roles | Notes |")
        lines.append("|------|-----------|-------|-------|")

        for tier_name, tier_def in access_tiers.items():
            resources = _list_str(tier_def.get("resources", []))
            tier_roles = _list_str(tier_def.get("roles", []))
            notes_parts = []
            req_for = tier_def.get("request_required_for", [])
            if req_for:
                notes_parts.append(f"request required for {', '.join(req_for)}")
            sla = tier_def.get("approval_sla_days")
            if sla is not None:
                notes_parts.append(f"approval SLA {sla}d")
            grant = tier_def.get("grant_duration_days")
            if grant is not None:
                notes_parts.append(f"grant duration {grant}d")
            notes = "; ".join(notes_parts) if notes_parts else ""
            lines.append(f"| `{tier_name}` | {resources} | {tier_roles} | {notes} |")

        lines.append("")

    return "\n".join(lines)


def generate_for_env(env_dir: Path, dry_run: bool = False) -> bool:
    """Generate docs/rbac_policy.md for one environment. Returns True on success."""
    yaml_path = env_dir / "policy" / "rbac_policy.yaml"
    if not yaml_path.exists():
        print(f"  SKIP {env_dir.name}: no policy/rbac_policy.yaml found")
        return False

    try:
        policy = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  ERROR {env_dir.name}: failed to parse YAML: {exc}", file=sys.stderr)
        return False

    markdown = render_rbac_markdown(env_dir.name, policy)

    docs_dir = env_dir / "docs"
    out_path = docs_dir / "rbac_policy.md"

    if dry_run:
        print(f"  DRY-RUN {env_dir.name}: would write {out_path}")
        return True

    docs_dir.mkdir(exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"  WROTE {out_path.relative_to(env_dir.parent.parent)}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-base",
        default=DEFAULT_ENV_BASE,
        help="Root directory containing env_*/ subdirectories",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without writing",
    )
    args = parser.parse_args(argv)

    env_base = Path(args.env_base)
    if not env_base.exists():
        print(f"ERROR: {env_base} does not exist", file=sys.stderr)
        return 1

    env_dirs = sorted(d for d in env_base.iterdir() if d.is_dir() and d.name.startswith("env_"))
    if not env_dirs:
        print(f"No env_*/ directories found under {env_base}", file=sys.stderr)
        return 1

    print(f"Generating RBAC policy docs for {len(env_dirs)} environment(s)...")
    ok = 0
    for env_dir in env_dirs:
        if generate_for_env(env_dir, dry_run=args.dry_run):
            ok += 1

    mode = "dry-run" if args.dry_run else "written"
    print(f"\nDone: {ok}/{len(env_dirs)} docs {mode}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
