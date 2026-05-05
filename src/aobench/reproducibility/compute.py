"""COMPUTE.jsonl schema and writer for AOBench reproducibility pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class ComputeRecord(BaseModel):
    """One row in COMPUTE.jsonl — per-task resource consumption record.

    COMPUTE.jsonl is a newline-delimited JSON file (one record per line)
    stored alongside MANIFEST.json in the run output directory.
    """

    run_id: str
    task_id: str
    model: str
    # Model identifier used for the agent on this task.

    prompt_tokens: Optional[int] = None
    # Input tokens consumed (across all turns for this task).

    completion_tokens: Optional[int] = None
    # Output tokens generated (across all turns for this task).

    cost_usd: Optional[float] = None
    # Estimated API cost in USD. None for open-weight / local runs.

    wall_clock_seconds: Optional[float] = None
    # Wall-clock time from task start to completion.

    open_weight: bool = False
    # True for locally-run open-weight models (e.g. Llama on GPU nodes).

    gpu_energy_wh: Optional[float] = None
    # GPU energy consumed in watt-hours (measured via NVML or similar).
    # None if energy measurement is unavailable.

    co2_g: Optional[float] = None
    # Estimated CO2 emissions in grams (gpu_energy_wh × grid_intensity).
    # None if energy data is unavailable.


def append_compute(record: ComputeRecord, output_dir: Path) -> None:
    """Append one ComputeRecord to COMPUTE.jsonl in output_dir.

    Creates the file if it does not exist. Each call appends exactly one
    newline-terminated JSON record (streaming / incremental write).

    Parameters
    ----------
    record:
        Populated ComputeRecord to serialise.
    output_dir:
        Directory containing COMPUTE.jsonl. Created if absent.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "COMPUTE.jsonl"
    line = json.dumps(record.model_dump(), default=str)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
