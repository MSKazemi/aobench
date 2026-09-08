#!/usr/bin/env python3
"""Extract a curated pool of REAL Marconi100 SLURM job records from M100 ExaData.

Reads the real ``job_table`` plugin parquet (``job_info_marconi100``) — one row per
job-state poll — dedups to the final record per ``job_id``, maps the real M100 fields onto
AOBench's ``SlurmJob`` schema, and writes a small, diverse, anonymized pool to
``benchmark/environments/_m100_reference/real_jobs.json``. The pool is small enough to commit,
so ``build_m100_bundles.py --real-jobs`` can ground env queues in real job characteristics
**offline**.

Real M100 ``job_state`` carries authentic terminal states including ``COMPLETED``, ``FAILED``,
``OUT_OF_MEMORY``, ``NODE_FAIL``, ``TIMEOUT`` and ``CANCELLED`` — so this unlocks real failure
grounding. ``user_id``/``partition``/``qos`` are already anonymized integers in the dataset.

Intended to run where the data lives (the ``n1`` server). First extract the job_table member
from a monthly tar, e.g.::

    tar -xf raw/22-07.tar --occurrence=1 \
        "year_month=22-07/plugin=job_table/metric=job_info_marconi100/a_0.parquet"

then::

    uv run --no-project --with pandas --with pyarrow python scripts/build_m100_jobs.py \
        --job-parquet <extracted a_0.parquet> --year-month 22-07 \
        --out benchmark/environments/_m100_reference/real_jobs.json

Provenance: CINECA Marconi100 ExaData dataset, doi:10.1038/s41597-023-02174-3.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

# Terminal states we curate (preferred when deduping a job's poll records).
_TERMINAL = ["COMPLETED", "FAILED", "OUT_OF_MEMORY", "NODE_FAIL", "TIMEOUT", "CANCELLED"]
# Per-state cap so the pool is diverse rather than dominated by COMPLETED.
_PER_STATE_CAP = 12
# Map M100 terminal states to AOBench canonical SlurmJob.state.
_STATE_CANON = {
    "OUT_OF_MEMORY": "FAILED", "NODE_FAIL": "FAILED", "TIMEOUT": "FAILED",
    "FAILED": "FAILED", "CANCELLED": "CANCELLED", "COMPLETED": "COMPLETED",
    "RUNNING": "RUNNING", "PENDING": "PENDING",
}


def parse_slurm_duration(s) -> int | None:
    """Parse a SLURM duration string ('D-HH:MM:SS' / 'HH:MM:SS' / 'MM:SS') to seconds."""
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return None
    s = str(s).strip()
    if not s or s in {"Unknown", "INVALID"}:
        return None
    days = 0
    if "-" in s:
        d, s = s.split("-", 1)
        try:
            days = int(d)
        except ValueError:
            return None
    parts = s.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 3:
        h, m, sec = nums
    elif len(nums) == 2:
        h, m, sec = 0, nums[0], nums[1]
    else:
        return None
    return days * 86400 + h * 3600 + m * 60 + sec


def seconds_to_elapsed(secs: int | None) -> str | None:
    if secs is None or secs < 0:
        return None
    h, rem = divmod(int(secs), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _clean(v):
    """Return a JSON-safe scalar (None for NaN/empty)."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    s = str(v).strip()
    return s if s and s.lower() != "nan" else None


def build_pool(df: pd.DataFrame, seed: int) -> list[dict]:
    """Dedup to final record per job_id and curate a diverse, mapped pool."""
    # Dedup: per job_id keep the most-terminal record (lowest rank), and among ties the
    # latest by schedule-eval time.
    order_col = "last_sched_eval" if "last_sched_eval" in df.columns else "eligible_time"
    df = df.copy()
    df["_term_rank"] = df["job_state"].map(
        {st: i for i, st in enumerate(_TERMINAL)}
    ).fillna(len(_TERMINAL))
    sort_cols, ascending = ["_term_rank"], [True]
    if order_col in df.columns:
        sort_cols.append(order_col)
        ascending.append(False)
    df = df.sort_values(sort_cols, ascending=ascending)
    df = df.groupby("job_id", as_index=False, sort=False).head(1)

    rng = pd.Series(range(len(df))).sample(frac=1.0, random_state=seed).index
    df = df.iloc[rng]

    pool: list[dict] = []
    per_state: dict[str, int] = {}
    for _, r in df.iterrows():
        state = _clean(r.get("job_state"))
        if state is None:
            continue
        num_cpus = r.get("num_cpus")
        try:
            num_cpus = int(num_cpus)
        except (ValueError, TypeError):
            continue
        if num_cpus < 1:
            continue
        if per_state.get(state, 0) >= _PER_STATE_CAP:
            continue
        # run_time / run_time_str are null in M100; derive duration from start/end times.
        run_s = parse_slurm_duration(r.get("run_time_str"))
        if run_s is None:
            st_t, en_t = r.get("start_time"), r.get("end_time")
            if pd.notna(st_t) and pd.notna(en_t):
                delta = (pd.Timestamp(en_t) - pd.Timestamp(st_t)).total_seconds()
                if delta and delta > 0:
                    run_s = int(delta)
        rec = {
            "job_id": _clean(r.get("job_id")),
            "user_id": _clean(r.get("user_id")),
            "partition": _clean(r.get("partition")),
            "qos": _clean(r.get("qos")),
            "job_state": state,
            "state": _STATE_CANON.get(state, state),
            "num_cpus": num_cpus,
            "num_nodes": int(r["num_nodes"]) if _clean(r.get("num_nodes")) else None,
            "run_time": run_s,
            "elapsed": seconds_to_elapsed(run_s),
            "time_limit": _clean(r.get("time_limit_str")),
            "derived_ec": _clean(r.get("derived_ec")),
            "exit_code": _clean(r.get("exit_code")),
            "state_reason": _clean(r.get("state_reason")),
            "min_memory_node": int(r["min_memory_node"]) if _clean(r.get("min_memory_node")) else None,
        }
        if rec["job_id"] is None:
            continue
        pool.append(rec)
        per_state[state] = per_state.get(state, 0) + 1
    return pool


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a real M100 job-record pool")
    ap.add_argument("--job-parquet", type=Path, required=True,
                    help="Path to the extracted job_info_marconi100 a_0.parquet")
    ap.add_argument("--year-month", default="unknown")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=388)
    args = ap.parse_args()

    df = pd.read_parquet(args.job_parquet)
    pool = build_pool(df, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "CINECA Marconi100 ExaData job_table (job_info_marconi100)",
        "year_month": args.year_month,
        "note": (
            "Curated, deduped pool of real anonymized M100 SLURM job records mapped to the "
            "AOBench SlurmJob schema. partition/qos/user_id are anonymized integers in the "
            "source data. job_state preserves real terminal states (incl. OUT_OF_MEMORY, "
            "NODE_FAIL, TIMEOUT). Nodes are intentionally omitted — the bundle builder assigns "
            "env nodes. Use via build_m100_bundles.py --real-jobs."
        ),
        "n_jobs": len(pool),
        "state_counts": {s: sum(1 for j in pool if j["job_state"] == s)
                         for s in sorted({j["job_state"] for j in pool})},
        "jobs": pool,
    }
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(pool)} real job records ({args.year_month}) → {args.out}")
    print("state counts:", payload["state_counts"])


if __name__ == "__main__":
    main()
