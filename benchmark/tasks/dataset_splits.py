# benchmark/tasks/dataset_splits.py
# WARNING: TEST_TASK_IDS must not be modified after the first model run.
# Modification after model runs constitutes result contamination.
# Last extended: 2026-05-02 (v3 taxonomy expansion — before any model runs)
# First frozen:  2026-03-21 (v0.1 core, JOB/MON/ENERGY × USR/SYS/FAC)

from __future__ import annotations

ALL_TASK_IDS: list[str] = []   # populated by task_loader.py at runtime

TEST_TASK_IDS: list[str] = [
    # ~25% held-out split — stratified by QCAT × role (71 tasks total, 18 held out).
    # Single-task strata (DATA/FAC/ARCH/DOCS for all roles, plus isolated RES/DES
    # strata in JOB/MON/ENERGY/PERF/SEC/AIOPS) are kept entirely in dev to preserve
    # at least one dev example per stratum.

    # ── JOB stratum (4 of 12) ──────────────────────────────────────────────
    "JOB_USR_002", "JOB_USR_004",   # scientific_user
    "JOB_SYS_002",                   # sysadmin
    "JOB_FAC_002",                   # facility_admin   (added v3)

    # ── MON stratum (4 of 11) ──────────────────────────────────────────────
    "MON_USR_002",                   # scientific_user
    "MON_SYS_003", "MON_SYS_005",   # sysadmin
    "MON_FAC_002",                   # facility_admin   (added v3)

    # ── ENERGY stratum (4 of 11) ───────────────────────────────────────────
    "ENERGY_USR_002",                # scientific_user
    "ENERGY_SYS_002",                # sysadmin
    "ENERGY_FAC_002", "ENERGY_FAC_004",  # facility_admin (FAC_002 added v3)

    # ── PERF stratum (2 of 6) — new in v3 ─────────────────────────────────
    "PERF_SYS_002",                  # sysadmin
    "PERF_USR_002",                  # scientific_user

    # ── SEC stratum (2 of 5) — new in v3 ──────────────────────────────────
    "SEC_SYS_002",                   # sysadmin
    "SEC_FAC_002",                   # facility_admin

    # ── AIOPS stratum (2 of 6) — new in v3 ────────────────────────────────
    "AIOPS_SYS_002",                 # sysadmin
    "AIOPS_FAC_002",                 # facility_admin

    # DATA / FAC / ARCH / DOCS: all strata have exactly 1 task → dev only
    # RES / DES roles: each QCAT has exactly 1 task → dev only
]

DEV_TASK_IDS: list[str] = []   # computed at runtime: ALL - TEST
LITE_TASK_IDS: list[str] = []  # populated by lite_selector.py after Stage 3

SPLIT_FROZEN_DATE: str = "2026-05-02"
SPLIT_FROZEN_CORPUS_VERSION: str = "v0.3"


def get_split(split: str) -> list[str]:
    """Return the task-ID list for the requested split name."""
    assert split in ("all", "dev", "test", "lite"), f"Unknown split: {split}"
    return {
        "all": ALL_TASK_IDS,
        "dev": DEV_TASK_IDS,
        "test": TEST_TASK_IDS,
        "lite": LITE_TASK_IDS,
    }[split]
