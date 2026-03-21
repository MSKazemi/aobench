# benchmark/tasks/dataset_splits.py
# WARNING: TEST_TASK_IDS must not be modified after the first model run.
# Modification after model runs constitutes result contamination.
# Last frozen: 2026-03-21 (before any model runs)

from __future__ import annotations

ALL_TASK_IDS: list[str] = []   # populated by task_loader.py at runtime

TEST_TASK_IDS: list[str] = [
    # 30% held-out split — stratified by QCAT × role
    # JOB stratum (3 of 10)
    "JOB_USR_002", "JOB_USR_004", "JOB_SYS_002",
    # MON stratum (3 of 10)
    "MON_USR_002", "MON_SYS_003", "MON_SYS_005",
    # ENERGY stratum (3 of 10)
    "ENERGY_USR_002", "ENERGY_SYS_002", "ENERGY_FAC_004",
    # PERF/DATA/SEC/FAC/ARCH/AIOPS/DOCS: extend here when tasks are written
]

DEV_TASK_IDS: list[str] = []   # computed at runtime: ALL - TEST
LITE_TASK_IDS: list[str] = []  # populated by lite_selector.py after Stage 3

SPLIT_FROZEN_DATE: str = "2026-03-21"
SPLIT_FROZEN_CORPUS_VERSION: str = "v0.1"


def get_split(split: str) -> list[str]:
    """Return the task-ID list for the requested split name."""
    assert split in ("all", "dev", "test", "lite"), f"Unknown split: {split}"
    return {
        "all": ALL_TASK_IDS,
        "dev": DEV_TASK_IDS,
        "test": TEST_TASK_IDS,
        "lite": LITE_TASK_IDS,
    }[split]
