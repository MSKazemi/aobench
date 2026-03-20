# Telemetry Query Guidelines

These guidelines apply to all `telemetry` queries against HPC monitoring data
(CPU, memory, GPU, network, power metrics collected per node).

## Metric Fields and Units

1. **CPU utilization** (`cpu_pct`): percentage 0–100. The complementary metric
   `cpu_idle_pct = 100 − cpu_pct`. High CPU utilization (>90%) is expected
   for compute-bound jobs; unusually high idle time may indicate a stalled job.

2. **Memory utilization** (`mem_pct`): percentage of physical RAM in use, 0–100.
   Values above 90% are a warning threshold; 97%+ typically precedes OOM events.
   Report the absolute value (e.g., "97.1% memory utilization"), not just
   "high memory."

3. **GPU utilization** (`gpu_pct`): percentage 0–100. For nodes without GPUs,
   this field is 0 — do not interpret as idle GPU. Check the node's hardware
   profile before inferring GPU idleness.

4. **Network I/O** (`net_rx_gbps`, `net_tx_gbps`): instantaneous throughput in
   **gigabytes per second (GB/s)**. For job-level totals, use cumulative
   `net_rx_gb` / `net_tx_gb` fields. Do not confuse GB/s with Gbps (bits).

5. **Power** (`power_kw`): instantaneous node power draw in **kilowatts (kW)**.
   Typical compute node: 1–4 kW. GPU nodes under load: 3–8 kW.

## Time Window Queries

6. **For time-range queries**, specify the window clearly using ISO 8601
   timestamps or relative windows (e.g., `window='last_6h'`). Telemetry is
   sampled at 60-second intervals by default. Report the number of samples
   used in any aggregation.

7. **Snapshot time anchor**: Use the snapshot's `snapshot_timestamp` as the
   "current time" for relative windows like "the last hour" or "today."
   Do not use real-world clock time.

## Anomaly Detection

8. **Memory anomaly indicators:**
   - Monotonic increase over time (memory leak pattern)
   - Rate of increase exceeds 5% per hour sustained for 2+ hours
   - Approaching 95%+ while the job is still running
   When reporting anomalies, always state the trend (e.g., "climbed from 65%
   to 97% over 6 hours") and the peak value with timestamp.

## Role Visibility for Telemetry

9. **scientific_user**: Only their own job's telemetry (cpu_pct, mem_pct,
   gpu_pct, net I/O on their allocated nodes during their job's runtime).
   **sysadmin / facility_admin / system_designer**: Full per-node telemetry
   for all nodes at any time.
   **researcher**: Aggregate partition metrics + own project jobs' telemetry.
   Never expose another user's per-job telemetry to a scientific_user.

## Aggregation Queries

10. **For percentile queries** (e.g., 95th percentile), clearly state the
    population size and time window. For example: *"The p95 memory usage
    across 156 running jobs is 87.4%."* Use standard statistical definitions
    (p95 = 95th percentile of the distribution, not the top 5% average).
