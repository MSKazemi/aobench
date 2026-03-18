# Cooling Failure Response Policy

## Thermal Thresholds

| Severity | Ambient Temp | Action Required |
|---|---|---|
| Normal   | < 25 °C      | No action |
| Warning  | 25–30 °C     | Monitor; inspect CRAC unit |
| Critical | > 30 °C      | Drain workloads; escalate to facilities |

## CPU Thermal Throttle

Nodes automatically reduce CPU frequency when the inlet temperature exceeds 30 °C:
- **Throttle level 1 (30–35 °C):** 20% frequency reduction
- **Throttle level 2 (> 35 °C):** 40% frequency reduction

Throttle state is reported in node power telemetry via `cpu_throttle_pct`.

## CRAC Unit Failure Response

1. Identify the affected rack zone from `crac_status.json`.
2. Check `rack_telemetry_*.csv` to confirm temperature rise.
3. Identify throttling nodes from `node_power_*.csv` (cpu_throttle_pct > 0).
4. Open or update incident record.
5. Drain affected nodes: `scontrol update NodeName=<node> State=DRAIN Reason="thermal"`
6. Deploy portable cooling or wait for CRAC repair.

## Escalation

- Facility team on-call: page via PagerDuty tag `facilities-oncall`
- Target response time for CRAC repair: 4 hours
