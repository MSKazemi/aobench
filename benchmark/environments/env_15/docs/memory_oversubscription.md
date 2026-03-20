# Memory Oversubscription and Enforcement

## Why oversubscription happens
- `--mem` in job script is a request, not a hard limit by default.
- If MaxMemPerNode is not enforced in SLURM, jobs can use more than requested.
- Multiple jobs on the same node can collectively exceed physical RAM.

## Symptoms
- node memory_util_pct > 100%
- Excessive swap I/O (disk_write_mbps spikes)
- Jobs run much slower than expected (CPU util drops due to I/O wait)

## Immediate response
1. Identify jobs on the affected node: `slurm query_jobs`.
2. Determine which job is using more than requested.
3. Cancel the lower-priority job: `scancel <jobid>`.
4. The remaining job should recover performance.

## Prevention
- Set `MaxMemPerNode` in partition config.
- Enable cgroup-based memory enforcement: `ConstrainRAMSpace=yes`.
- Run `scontrol show config | grep Memory` to verify enforcement is active.
