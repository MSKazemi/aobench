# Cooling Operations Runbook — AOBench Cluster B

## ASHRAE A2 Thermal Envelope
Per ASHRAE A2 guidelines, compute equipment must operate within:
- Inlet temperature: **10°C – 35°C** (dry bulb, 27°C max recommended)
- Relative humidity: 8% – 80% (non-condensing)
- Temperature change rate: ≤ 5°C/hour

Equipment exceeding 35°C inlet is at risk of thermal throttling or shutdown.

## Procedure: Responding to CRAC Unit Fault
1. **Acknowledge alarm** in BMS console (inhibit re-alarm for 30 min)
2. **Check adjacent CRACs** — verify they have capacity to absorb load
3. **Reduce IT load**: contact sysadmin to drain hot-row nodes and migrate jobs
4. **Dispatch facilities tech**: file work order in CMDB, escalation SLA = 2 hours for CRITICAL
5. **Monitor inlet temps** every 5 minutes; if row inlet > 38°C, initiate emergency load shedding

## CRAC Capacity Planning
Each CRAC unit (25–30 kW) serves one hot-aisle/cold-aisle row pair. Maximum sustained IT load per CRAC: 80% of rated capacity (24 kW for 30 kW unit).
