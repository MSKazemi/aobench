# Lustre I/O Troubleshooting Guide

## Lustre bandwidth limits
- Aggregate OST write bandwidth: ~3.2 GB/s (4 OSTs × 800 MB/s)
- If one job consumes all OST bandwidth, other jobs see near-zero I/O

## Identifying the I/O offender
1. Query telemetry for `disk_write_mbps` across all nodes.
2. High writers (>500 MB/s per node) are suspects.
3. Correlate with SLURM job list to find the account and user.

## Throttling I/O on Lustre
- Apply per-job I/O limit (if MDS jobstats enabled):
  `lctl set_param llite.*.max_dirty_mb=256`
- Or cancel the offending job after notifying user.

## Scheduling I/O-heavy jobs
- Submit checkpoint jobs during off-peak hours (nights/weekends).
- Use `--exclusive` for I/O-intensive jobs to isolate them.
- Consider separate I/O queue for checkpoint/backup workloads.
