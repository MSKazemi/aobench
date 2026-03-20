# Capacity Planning Guide

## Saturation thresholds
- 85%: Begin capacity planning process
- 90%: Order hardware (assuming 12-week delivery)
- 95%: Queue times become unacceptable (>4h average wait)
- 100%: New jobs cannot start

## Expansion options
1. Add compute nodes to existing cluster (fastest, 8–12 weeks)
2. Burst to cloud (immediate, higher cost per CPU-hour)
3. Add new rack section (16–20 weeks — facility work required)

## Forecasting methodology
- Use 90-day rolling average to smooth seasonal variation
- Linear extrapolation for 6-week horizon
- Flag if growth rate changes >2 pp/month

## Data sources
- CPU utilisation: `telemetry query_timeseries metric_name=cpu_util_pct`
- Job queue depth: `slurm query_jobs state=PENDING`
- Historical sacct: available via the reporting portal
