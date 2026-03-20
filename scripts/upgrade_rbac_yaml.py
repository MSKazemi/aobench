#!/usr/bin/env python3
"""Upgrade all rbac_policy.yaml files from v1.0 to v1.1.

Adds:
- All 5 roles (scientific_user, researcher, sysadmin, facility_admin, system_designer)
- allowed_tools per role
- partition_access per role
- access_tiers top-level section
- version bump to "1.1"

Preserves all existing role permissions and descriptions.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ENVS_ROOT = Path(__file__).parent.parent / "benchmark" / "environments"

# Canonical baseline permissions for roles not present in a file
BASELINE_PERMISSIONS: dict[str, list[dict]] = {
    "scientific_user": [
        {"resource": "slurm.jobs", "actions": ["read_own"], "constraint": "user == requester"},
        {"resource": "slurm.partitions", "actions": ["read"]},
        {"resource": "docs", "actions": ["read"]},
        {"resource": "telemetry.memory_events", "actions": ["read_own"], "constraint": "job_id in requester_jobs"},
        {"resource": "incidents", "actions": []},
    ],
    "researcher": [
        {"resource": "slurm.jobs", "actions": ["read_own", "read_project"], "constraint": "project == requester_project"},
        {"resource": "slurm.nodes", "actions": []},
        {"resource": "slurm.partitions", "actions": ["read"]},
        {"resource": "docs", "actions": ["read"]},
        {"resource": "telemetry.*", "actions": ["read_own"], "constraint": "node in requester_job_nodes"},
        {"resource": "incidents", "actions": []},
    ],
    "sysadmin": [
        {"resource": "slurm.jobs", "actions": ["read", "modify", "cancel"]},
        {"resource": "slurm.nodes", "actions": ["read", "drain", "resume"]},
        {"resource": "slurm.partitions", "actions": ["read", "modify"]},
        {"resource": "docs", "actions": ["read"]},
        {"resource": "telemetry.*", "actions": ["read"]},
        {"resource": "incidents", "actions": ["read", "update"]},
    ],
    "facility_admin": [
        {"resource": "*", "actions": ["*"]},
    ],
    "system_designer": [
        {"resource": "slurm.*", "actions": ["read"]},
        {"resource": "telemetry.*", "actions": ["read"]},
        {"resource": "energy_data", "actions": ["read"]},
        {"resource": "facility_data", "actions": ["read"]},
        {"resource": "docs", "actions": ["read"]},
    ],
}

BASELINE_DESCRIPTIONS: dict[str, str] = {
    "scientific_user": "HPC user — can view their own jobs only",
    "researcher": "Elevated user — project-level access",
    "sysadmin": "System administrator — full operational access",
    "facility_admin": "Facility administrator — full access",
    "system_designer": "Systems analyst — full read-only for capacity planning",
}

ALLOWED_TOOLS: dict[str, list[str]] = {
    "scientific_user": ["slurm", "rbac", "docs"],
    "researcher": ["slurm", "telemetry", "rbac", "docs"],
    "sysadmin": ["slurm", "telemetry", "rbac", "docs", "facility", "incidents"],
    "facility_admin": ["*"],
    "system_designer": ["slurm", "telemetry", "facility", "rbac", "docs"],
}

PARTITION_ACCESS: dict[str, list[dict]] = {
    "scientific_user": [
        {"name": "cpu", "max_walltime": "48:00:00"},
        {"name": "debug", "max_walltime": "01:00:00"},
    ],
    "researcher": [
        {"name": "cpu", "max_walltime": "48:00:00"},
        {"name": "gpu", "max_walltime": "72:00:00"},
        {"name": "debug", "max_walltime": "01:00:00"},
    ],
    "sysadmin": [
        {"name": "*", "max_walltime": "168:00:00"},
    ],
    "facility_admin": [
        {"name": "*", "max_walltime": "168:00:00"},
    ],
    "system_designer": [
        {"name": "cpu", "max_walltime": "48:00:00"},
        {"name": "debug", "max_walltime": "01:00:00"},
    ],
}

ACCESS_TIERS: dict = {
    "tier1_public": {
        "resources": ["slurm.partitions", "docs", "slurm.jobs"],
        "roles": ["*"],
    },
    "tier2_privileged": {
        "resources": ["slurm.jobs", "slurm.nodes", "telemetry.*", "incidents"],
        "roles": ["sysadmin", "facility_admin"],
        "request_required_for": ["scientific_user", "researcher"],
        "approval_sla_days": 2,
        "grant_duration_days": 90,
    },
    "tier3_restricted": {
        "resources": ["energy_data", "facility_data"],
        "roles": ["facility_admin", "system_designer"],
    },
    "tier4_sensitive": {
        "resources": ["audit_logs", "procurement"],
        "roles": [],
    },
}

ALL_ROLES = ["scientific_user", "researcher", "sysadmin", "facility_admin", "system_designer"]


def upgrade_policy(policy: dict) -> dict:
    """Return an upgraded copy of a policy dict."""
    roles = policy.get("roles", {})

    # Add missing roles
    for role in ALL_ROLES:
        if role not in roles:
            roles[role] = {
                "description": BASELINE_DESCRIPTIONS[role],
                "permissions": BASELINE_PERMISSIONS[role],
            }
        else:
            # Ensure description exists
            if "description" not in roles[role]:
                roles[role]["description"] = BASELINE_DESCRIPTIONS[role]
            # Ensure permissions exists
            if "permissions" not in roles[role]:
                roles[role]["permissions"] = BASELINE_PERMISSIONS[role]

        # Add allowed_tools if missing
        if "allowed_tools" not in roles[role]:
            roles[role]["allowed_tools"] = ALLOWED_TOOLS[role]

        # Add partition_access if missing
        if "partition_access" not in roles[role]:
            roles[role]["partition_access"] = PARTITION_ACCESS[role]

    return {
        "version": "1.1",
        "roles": roles,
        "access_tiers": ACCESS_TIERS,
        "hard_fail_on_violation": policy.get("hard_fail_on_violation", True),
    }


def process_env(env_dir: Path) -> None:
    policy_path = env_dir / "policy" / "rbac_policy.yaml"
    if not policy_path.exists():
        print(f"  SKIP — no rbac_policy.yaml: {env_dir.name}")
        return

    with policy_path.open() as f:
        policy = yaml.safe_load(f) or {}

    if policy.get("version") == "1.1":
        print(f"  SKIP — already v1.1: {env_dir.name}")
        return

    upgraded = upgrade_policy(policy)

    with policy_path.open("w") as f:
        yaml.dump(upgraded, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"  UPGRADED: {env_dir.name}")


def main() -> None:
    env_dirs = sorted(ENVS_ROOT.glob("env_*"))
    print(f"Processing {len(env_dirs)} environments...")
    for env_dir in env_dirs:
        process_env(env_dir)
    print("Done.")


if __name__ == "__main__":
    main()
