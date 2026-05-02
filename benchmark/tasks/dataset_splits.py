# benchmark/tasks/dataset_splits.py
# WARNING: TEST_TASK_IDS must not be modified after the first model run.
# Modification after model runs constitutes result contamination.
# Last reconciled: 2026-05-03 (Option B — all 10 QCATs in scope, 80 tasks total)
# First frozen:    2026-03-21 (v0.1 core, JOB/MON/ENERGY × USR/SYS/FAC)
#
# Split selection logic (deterministic, reproducible):
#   1. Group all 80 tasks by (QCAT × role) stratum.
#   2. For strata with ≥ 2 tasks: sort by descending difficulty (hard > medium > easy),
#      then ascending task_id; take the first task as TEST.  One dev example always
#      remains in each such stratum.
#   3. For QCATs whose every stratum has exactly 1 task (DATA, DOCS, FAC): pick the
#      single hardest task in that QCAT (ties broken by ascending task_id) to ensure
#      all 10 QCATs appear in the test set.
#   Result: 21 test tasks (~26%), 59 dev tasks (~74%).

from __future__ import annotations

ALL_TASK_IDS: list[str] = []   # populated by task_loader.py at runtime

TEST_TASK_IDS: list[str] = [
    # ── AIOPS (2 of 7) ────────────────────────────────────────────────────
    "AIOPS_FAC_001",   # facility_admin  medium  (FAC stratum ≥2)
    "AIOPS_SYS_002",   # sysadmin        hard    (SYS stratum ≥2)

    # ── ARCH (1 of 6) ─────────────────────────────────────────────────────
    "ARCH_DES_001",    # system_designer hard    (DES stratum ≥2)

    # ── DATA (1 of 5) — all strata singleton; hardest task picked ─────────
    "DATA_DES_001",    # system_designer hard

    # ── DOCS (1 of 5) — all strata singleton; hardest task picked ─────────
    "DOCS_DES_001",    # system_designer medium

    # ── ENERGY (3 of 12) ──────────────────────────────────────────────────
    "ENERGY_FAC_002",  # facility_admin  hard    (FAC stratum ≥2)
    "ENERGY_SYS_002",  # sysadmin        medium  (SYS stratum ≥2)
    "ENERGY_USR_002",  # scientific_user medium  (USR stratum ≥2)

    # ── FAC (1 of 5) — all strata singleton; hardest task picked ──────────
    "FAC_DES_001",     # system_designer hard

    # ── JOB (3 of 12) ─────────────────────────────────────────────────────
    "JOB_FAC_001",     # facility_admin  medium  (FAC stratum ≥2)
    "JOB_SYS_002",     # sysadmin        hard    (SYS stratum ≥2)
    "JOB_USR_004",     # scientific_user hard    (USR stratum ≥2)

    # ── MON (4 of 13) ─────────────────────────────────────────────────────
    "MON_FAC_002",     # facility_admin  medium  (FAC stratum ≥2)
    "MON_RES_001",     # researcher      hard    (RES stratum ≥2)
    "MON_SYS_005",     # sysadmin        hard    (SYS stratum ≥2)
    "MON_USR_002",     # scientific_user medium  (USR stratum ≥2)

    # ── PERF (2 of 7) ─────────────────────────────────────────────────────
    "PERF_SYS_002",    # sysadmin        hard    (SYS stratum ≥2)
    "PERF_USR_002",    # scientific_user medium  (USR stratum ≥2)

    # ── SEC (3 of 8) ──────────────────────────────────────────────────────
    "SEC_FAC_002",     # facility_admin  hard    (FAC stratum ≥2)
    "SEC_SYS_002",     # sysadmin        hard    (SYS stratum ≥2)
    "SEC_USR_001",     # scientific_user easy    (USR stratum ≥2, lowest task_id)
]

DEV_TASK_IDS: list[str] = []   # computed at runtime: ALL - TEST
LITE_TASK_IDS: list[str] = []  # populated by lite_selector.py after Stage 3

SPLIT_FROZEN_DATE: str = "2026-05-03"
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
