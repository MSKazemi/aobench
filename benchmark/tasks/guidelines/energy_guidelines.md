# Energy Query Guidelines

These guidelines apply to all `energy` queries covering power draw, energy
consumption, efficiency metrics, and budget tracking.

## Units — Critical

1. **Power** is measured in **kilowatts (kW)**. **Energy** is measured in
   **kilowatt-hours (kWh)**. Never confuse the two. Always include the unit
   in your answer. For example: *"The cluster draws 847.2 kW"* (power) vs.
   *"The gpu partition consumed 14,832 kWh yesterday"* (energy).

2. **Energy efficiency** is reported as **GFLOPS/Watt** (gigaflops per watt).
   Higher is better. Typical HPC GPU nodes achieve 10–35 GFLOPS/Watt depending
   on workload. Do not report efficiency as FLOPS/kW or other non-standard units.

3. **Conversion reminder:** 1 kW sustained for 1 hour = 1 kWh. For short
   bursts (minutes), use kW × (minutes / 60) = kWh.

## Field Names

4. **Power fields:** `power_kw` (instantaneous, per node), `total_power_kw`
   (cluster-wide instantaneous sum). **Energy fields:** `energy_kwh`
   (cumulative per job or per node over a period). Use the correct field
   for the question — do not report cumulative energy as instantaneous power.

## Role Visibility for Energy Data

5. **scientific_user**: Only their own job's energy consumption (`energy_kwh`
   for their job_id). They cannot see other users' job energy or cluster totals.
   **researcher**: Project-level energy summaries (aggregate over project jobs).
   **facility_admin / system_designer**: Full cluster energy, per-partition
   breakdowns, budget tracking, and efficiency metrics.
   **sysadmin**: Full energy data (for incident response and power spikes).

## Budget and Capacity

6. **Monthly energy budget** is expressed as a total kWh cap for the facility.
   Percentage consumed = `monthly_used_kwh / monthly_budget_kwh × 100`.
   When reporting budget status, always state: % used, absolute kWh used,
   kWh remaining, and estimated days until budget exhaustion at current rate.

7. **Cluster power capacity** is the maximum safe power draw in kW (typically
   set by the facility's electrical infrastructure). Utilization =
   `total_power_kw / capacity_kw × 100`. Alert threshold is typically 85–90%.

## Power Spike Events

8. **Power spikes** are sudden increases in cluster power draw exceeding the
   normal operating band. To correlate a power spike with running jobs:
   query all jobs in `RUNNING` state at the spike timestamp using
   `slurm_tool(method='job_history', state='RUNNING', at_time=<timestamp>)`.
   Report the spike magnitude (kW above baseline) and duration (minutes).

## Energy Trend Queries

9. **For trend queries** (e.g., "over the last 7 days"), report both the
   start value, end value, absolute change, and percentage change. Identify
   whether the trend is increasing, decreasing, or flat based on the slope
   (not just the endpoints).

## Efficiency Recommendations

10. **When recommending energy reduction actions**, prioritize by impact:
    (1) scheduling large jobs during off-peak hours improves cooling efficiency
        (PUE improvement of 5–15% typical at night),
    (2) per-job energy caps enforce accountability and prevent runaway jobs,
    (3) job type routing (e.g., inference to more efficient hardware),
    (4) aggressive idle power states for unallocated nodes.
    Always quantify the expected impact in kWh or % when making recommendations.
