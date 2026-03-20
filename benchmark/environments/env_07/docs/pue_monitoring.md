# PUE Monitoring and Alerting

## Baseline and thresholds
- Target PUE: 1.35
- Warning threshold: 1.45
- Critical threshold: 1.55

## Inlet temperature limits
- Normal operating range: 18–27°C
- Warning: >27°C for any rack row
- Critical: >32°C — throttle or evacuate

## CRAC unit roles
- CRAC-1: rows A–B (nodes 01–16)
- CRAC-2: rows C–D (nodes 17–32)
- CRAC-3: backup / overflow

## Remediation steps
1. Check CRAC unit status via BMS.
2. If airflow reduced: inspect/replace filter.
3. Enable CRAC-3 backup while servicing primary.
4. Monitor PUE recovery over 30-min windows.
