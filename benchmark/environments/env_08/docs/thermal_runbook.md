# Thermal Management Runbook

## Normal CPU temperature ranges
- Idle: 40–55°C
- Full load: 65–75°C
- Throttle threshold: 80°C (hardware-enforced)
- Emergency shutdown: 95°C

## Symptoms of thermal throttling
- Reduced CPU utilization despite full job load
- SLURM job runtime significantly longer than expected
- cpu_temp_c metric consistently above 80°C

## Immediate response
1. Identify affected node: query telemetry for cpu_temp_c > 80°C.
2. Drain node: `scontrol update nodename=<node> state=drain reason="thermal_throttle"`.
3. Migrate any queued jobs to healthy nodes.
4. Inspect cooling duct and fans.

## Root causes
- Blocked rear duct (dust, cable obstruction)
- Failed fan
- CRAC unit insufficient capacity in rack section
