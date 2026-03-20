# Fairshare Scheduling Policy

## How fairshare works
- Each account has a fairshare weight (proportional to allocation size).
- Jobs from accounts that have used more than their share get lower priority.
- Fairshare score decays over a half-life period (default: 14 days).

## Priority formula
`Job Priority = (Fairshare × W_fs) + (Age × W_age) + (QOS × W_qos)`

## Starvation prevention
- `PriorityDecayHalfLife` = 14 days
- `PriorityMaxAge` = 7 days (age boost caps at 7 days of waiting)
- After 7 days, a starving job still may not start if fairshare delta is extreme.

## Sysadmin interventions
- Boost a starving job: `scontrol update jobid=<id> priority=<high>`
- Hold monopolizing account: `scontrol update account=<acct> maxsubmitjobs=0`
- Reset fairshare counters: `sacctmgr modify account <acct> set rawusage=0`
