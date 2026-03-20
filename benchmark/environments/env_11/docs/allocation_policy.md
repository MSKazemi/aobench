# CPU-Hour Allocation Policy

## Allocation periods
- Billing period: calendar month (reset on the 1st)
- Allocations are per-account (not per-user within an account)

## QOS limits enforcement
- At 90%: warning email to PI
- At 100%: all new jobs blocked (QOSMaxCpuMinutesPerJobLimit)
- Running jobs are NOT affected — only new submissions blocked

## Emergency extensions
- PI submits request to allocations@hpc.example.edu
- facility_admin reviews and may grant up to 20% overage
- Overage is deducted from next month's allocation

## Checking account usage
- `sacct -A <account> --format=CPUTimeRAW --starttime=<first-of-month>`
- Divide by 60 for CPU-hours
