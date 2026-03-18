# Rack Status — Snapshot 2026-02-20T08:55:00Z

## Summary

| Rack   | Nodes | Cooling | Ambient °C | Hotspot °C | Status   |
|--------|-------|---------|------------|------------|----------|
| rack-a | 3     | ok      | 22.2       | 28.5       | Normal   |
| rack-b | 3     | ok      | 21.7       | 27.8       | Normal   |
| rack-c | 4     | FAILED  | 35.8       | 42.3       | Critical |
| rack-d | 2     | ok      | 22.5       | 29.2       | Normal   |

## rack-c Details

CRAC unit **crac-c1** failed at 08:41 UTC (COMPRESSOR_FAULT).
Nodes in rack-c are thermal-throttling at 40% CPU frequency reduction.

Affected nodes: node-c01, node-c02, node-c03, node-c04
Throttle level: 40% (cpu_freq: 3200 MHz → 1920 MHz)
Average node power draw: ~1.10 kW (vs normal ~1.81 kW)
