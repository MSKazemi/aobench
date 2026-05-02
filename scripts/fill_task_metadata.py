#!/usr/bin/env python3
"""Fill missing metadata fields in all task spec JSON files."""
import json
import glob

KSS_MAP = {
    ("scientific_user", "JOB"):    ["USR_DOC", "WIKI"],
    ("scientific_user", "MON"):    ["USR_DOC", "WIKI"],
    ("scientific_user", "ENERGY"): ["USR_DOC"],
    ("scientific_user", "PERF"):   ["USR_DOC"],
    ("scientific_user", "DATA"):   ["USR_DOC", "WIKI"],
    ("scientific_user", "SEC"):    ["USR_DOC", "POLICY"],
    ("scientific_user", "FAC"):    ["USR_DOC"],
    ("scientific_user", "ARCH"):   ["USR_DOC", "ARCH_DOC"],
    ("scientific_user", "AIOPS"):  ["USR_DOC"],
    ("scientific_user", "DOCS"):   ["USR_DOC", "WIKI"],
    ("sysadmin", "JOB"):           ["OPS_DOC", "POLICY"],
    ("sysadmin", "MON"):           ["OPS_DOC", "POLICY"],
    ("sysadmin", "ENERGY"):        ["OPS_DOC", "FAC_DOC"],
    ("sysadmin", "PERF"):          ["OPS_DOC", "ARCH_DOC"],
    ("sysadmin", "DATA"):          ["OPS_DOC", "DATA_GOV"],
    ("sysadmin", "SEC"):           ["OPS_DOC", "POLICY"],
    ("sysadmin", "FAC"):           ["OPS_DOC", "FAC_DOC"],
    ("sysadmin", "ARCH"):          ["OPS_DOC", "ARCH_DOC"],
    ("sysadmin", "AIOPS"):         ["OPS_DOC", "WIKI"],
    ("sysadmin", "DOCS"):          ["OPS_DOC", "WIKI"],
    ("facility_admin", "JOB"):     ["FAC_DOC", "OPS_DOC"],
    ("facility_admin", "MON"):     ["FAC_DOC", "OPS_DOC"],
    ("facility_admin", "ENERGY"):  ["FAC_DOC", "REF_STD"],
    ("facility_admin", "PERF"):    ["FAC_DOC", "OPS_DOC"],
    ("facility_admin", "DATA"):    ["FAC_DOC", "DATA_GOV"],
    ("facility_admin", "SEC"):     ["FAC_DOC", "POLICY"],
    ("facility_admin", "FAC"):     ["FAC_DOC", "REF_STD"],
    ("facility_admin", "ARCH"):    ["FAC_DOC", "ARCH_DOC"],
    ("facility_admin", "AIOPS"):   ["FAC_DOC", "OPS_DOC"],
    ("facility_admin", "DOCS"):    ["FAC_DOC", "WIKI"],
    ("researcher", "JOB"):         ["OPS_DOC", "WIKI"],
    ("researcher", "MON"):         ["OPS_DOC", "WIKI"],
    ("researcher", "ENERGY"):      ["OPS_DOC", "WIKI"],
    ("researcher", "DATA"):        ["DATA_GOV", "WIKI"],
    ("researcher", "FAC"):         ["FAC_DOC", "WIKI"],
    ("researcher", "ARCH"):        ["ARCH_DOC", "WIKI"],
    ("researcher", "DOCS"):        ["WIKI", "USR_DOC"],
    ("system_designer", "JOB"):    ["OPS_DOC", "ARCH_DOC"],
    ("system_designer", "MON"):    ["OPS_DOC", "ARCH_DOC"],
    ("system_designer", "ENERGY"): ["ARCH_DOC", "ENG_DOC"],
    ("system_designer", "PERF"):   ["ARCH_DOC", "ENG_DOC"],
    ("system_designer", "DATA"):   ["ARCH_DOC", "DATA_GOV"],
    ("system_designer", "SEC"):    ["ARCH_DOC", "POLICY"],
    ("system_designer", "FAC"):    ["FAC_DOC", "ENG_DOC"],
    ("system_designer", "ARCH"):   ["ARCH_DOC", "ENG_DOC"],
    ("system_designer", "AIOPS"):  ["ARCH_DOC", "ENG_DOC"],
    ("system_designer", "DOCS"):   ["ENG_DOC", "WIKI"],
}

TIER_MAP = {
    "scientific_user":  "tier1_public",
    "researcher":       "tier3_restricted",
    "sysadmin":         "tier2_privileged",
    "facility_admin":   "tier2_privileged",
    "system_designer":  "tier4_sensitive",
}

PROFILE_MAP = {
    "scientific_user":  "default_hpc_v01",
    "researcher":       "default_hpc_v01",
    "sysadmin":         "alpha1_grounding",
    "facility_admin":   "alpha1_grounding",
    "system_designer":  "alpha1_grounding",
}

DIFFICULTY_TIER_MAP = {"easy": 1, "medium": 2, "hard": 3, "adversarial": 3}

specs_dir = "benchmark/tasks/specs"
updated = 0
for path in sorted(glob.glob(f"{specs_dir}/*.json")):
    with open(path) as f:
        t = json.load(f)
    role, qcat = t["role"], t["qcat"]
    changed = False
    key = (role, qcat)

    if not t.get("knowledge_source_scope") and key in KSS_MAP:
        t["knowledge_source_scope"] = KSS_MAP[key]
        changed = True

    if not t.get("access_tier") and role in TIER_MAP:
        t["access_tier"] = TIER_MAP[role]
        changed = True

    if not t.get("aggregate_weight_profile") and role in PROFILE_MAP:
        t["aggregate_weight_profile"] = PROFILE_MAP[role]
        changed = True

    if "difficulty_tier" not in t:
        diff = t.get("difficulty", "medium")
        t["difficulty_tier"] = DIFFICULTY_TIER_MAP.get(diff, 2)
        changed = True

    if "task_creation_date" not in t:
        t["task_creation_date"] = "2026-05-02"
        changed = True

    if "contamination_risk" not in t:
        t["contamination_risk"] = "clean"
        changed = True

    if changed:
        with open(path, "w") as f:
            json.dump(t, f, indent=2)
            f.write("\n")
        updated += 1

print(f"Updated {updated} task specs")
