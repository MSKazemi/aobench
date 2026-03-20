# GPU Idle Policy

## Energy context
- GPU nodes draw ~400W at idle (A100 80GB base power)
- At cluster scale, idle GPUs represent significant avoidable cost
- 1 idle GPU node for 24 hours = 9.6 kWh wasted

## Idle timeout policy
- Warning to user: GPU util <10% for >2 hours (automated email)
- Sysadmin review: GPU util <5% for >4 hours
- Cancellation eligible: GPU util <2% for >6 hours, with user notification

## Facility_admin actions
1. Query telemetry: `telemetry query_timeseries metric_name=gpu_util_pct`
2. Identify nodes with sustained near-zero GPU util
3. Contact user via helpdesk ticket before cancellation
4. Cancel job if no response within 1 hour: `scancel <jobid>`

## Prevention
- Submit jobs with `--time` limits appropriate to actual workload
- Use `seff <jobid>` after completion to assess GPU efficiency
- Consider job arrays instead of holding GPUs for batch processing
