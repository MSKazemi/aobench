# Fidelity Report: env_07
Generated: 2026-05-02T23:10:26.612529+00:00

## F1 — ✓ PASS
- Metric: lognormal_mu
- Value: 8.82
- Expected: μ∈[6.3,9.3] σ∈[1.4,2.4]
- μ=8.820 (OK), σ=1.618 (OK)

## F2 — ✓ PASS
- Metric: powerlaw_alpha
- Value: 1.518
- Expected: α∈[1.4,2.0]
- α=1.518 (OK)

## F3 — ✓ PASS
- Metric: completed_fraction
- Value: 0.7143
- Expected: COMPLETED∈[68%,88%] FAILED∈[0%,19%]
- COMPLETED=71.4% (OK), FAILED=0.0% (OK)

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
- Value: 6
- Expected: len(roles)>=2
- found 6 roles: ['*', 'facility_admin', 'researcher', 'scientific_user', 'sysadmin', 'system_designer']

## F7 — ✓ PASS
- Metric: tool_catalog
- Expected: all methods have descriptions
- skipped

**Overall: PASS**