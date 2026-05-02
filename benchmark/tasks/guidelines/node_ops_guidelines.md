# Node Operations Query Guidelines

These guidelines apply to all `node_ops` queries against SLURM node state data.

## Node Identity

1. **Use `node_id` (e.g., `node042`) as the primary key** for node lookups.
   Node IDs follow the pattern `node<NNN>` with zero-padded three-digit numbers.
   Do not confuse node IDs with hostnames or IP addresses.

## Node State Values

2. **Valid SLURM node states are:** `IDLE`, `ALLOCATED`, `MIXED`, `DRAIN`,
   `DOWN`, `MAINT`, `RESERVED`. Always report the exact state string.
   - `IDLE` — node is up and available, no jobs running
   - `ALLOCATED` — all CPUs/GPUs assigned to running jobs
   - `MIXED` — some (but not all) CPUs/GPUs assigned
   - `DRAIN` — node is being drained; no new jobs will be scheduled,
               but existing jobs continue until completion
   - `DOWN` — node is unavailable (hardware fault, network issue, etc.)
   - `MAINT` — node is under scheduled maintenance

3. **DRAIN vs DOWN:** A node in `DRAIN` state is not failed — it is being
   gracefully removed from service. A node in `DOWN` state is unavailable.
   Do not conflate these when reporting node health.

## Drain Reason and Duration

4. **Always report the drain reason** when answering questions about draining
   nodes. The reason field explains *why* the node was drained (e.g.,
   "thermal throttling", "memory ECC errors", "scheduled maintenance").

5. **Drain duration** = current time − `state_since` timestamp. Report as
   hours and minutes (e.g., "draining for 6h 12m"). Use the snapshot
   timestamp as "current time" for deterministic evaluation.

## Utilization Calculations

6. **Utilization rate** = `cpu_alloc / cpu_total × 100%`. For GPU partitions,
   also report `gpu_alloc / gpu_total`. Always state both numerator and
   denominator (e.g., "39 of 50 nodes allocated = 78%").

7. **Idle proportion** = `idle_nodes / total_nodes × 100%`. Do not include
   `DOWN` or `DRAIN` nodes in the idle count — they are unavailable, not idle.

## Role Visibility

8. **All roles** can see aggregate partition state (node counts, utilization %).
   Only **sysadmin**, **facility_admin**, and **system_designer** can see
   per-node details (individual node IDs, drain reasons, hardware fault details).
   system_designer access to per-node data is scoped to topology and capacity
   planning — not operational incident response.

## Partition Scope

9. **When answering partition-level questions**, query all active partitions
   (`cpu`, `gpu`, `highmem`, `debug`) unless a specific partition is named.
   The `restricted` partition is administrative and should not appear in
   general utilization reports.

## Hardware Fault Context

10. **Thermal throttling** is indicated by CPU temperature above 85°C and/or
    reduced CPU frequency. It does not immediately cause node failure but
    degrades job performance. Recommend drain + inspection when temperature
    exceeds 90°C or CPU frequency is reduced by more than 20%.
