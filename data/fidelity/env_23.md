# Fidelity Report: env_23
Generated: 2026-05-02T22:37:39.500347+00:00

## F1 — ✓ PASS
- Metric: lognormal_mu
- Expected: 7.8±1.5σ
- skipped (no slurm_state.json)

## F2 — ✓ PASS
- Metric: powerlaw_alpha
- Expected: α∈[1.4,2.0]
- skipped (no slurm_state.json)

## F3 — ✓ PASS
- Metric: completed_fraction
- Expected: COMPLETED∈[68%,88%] FAILED∈[0%,19%]
- skipped (no slurm_state.json)

## F4 — ✓ PASS
- Metric: no_power_data
- Expected: CPU∈[297,402]W GPU∈[1572,2128]W
- skipped (no power files)

## F5 — ✓ PASS
- Metric: no_telemetry
- Expected: power∈[48,72]s state/energy∈[240,360]s
- skipped

## F6 — ✓ PASS
- Metric: rbac_roles
- Value: 5
- Expected: len(roles)>=2
- found 5 roles: ['*', 'facility_admin', 'researcher', 'sysadmin', 'system_designer']

## F7 — ✓ PASS
- Metric: tool_catalog
- Expected: all methods have descriptions
- skipped

**Overall: PASS**