# Partition Access Policy

## standard partition
- Available to: all registered users and accounts
- Max walltime: 48 hours
- Memory per node: 256 GB

## restricted partition
- Available to: approved research groups only (AllowAccounts list)
- Requires: PI approval + sysadmin account addition
- Max walltime: 168 hours (1 week)
- Memory per node: 1 TB (high-memory nodes)

## Requesting restricted access
1. PI submits access request to helpdesk@hpc.example.edu.
2. Sysadmin adds account to AllowAccounts in slurm.conf.
3. User is notified and may resubmit.

## If a job is held (PartitionNotAvailable)
- The job will remain PENDING indefinitely.
- Cancel and resubmit to the correct partition, or request access.
- `scancel <jobid>` to remove the held job.
