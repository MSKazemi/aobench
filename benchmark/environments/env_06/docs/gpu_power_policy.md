# GPU Partition Power Policy

## Per-node power limits
- Baseline TDP per GPU node: ~380W (4× A100 80GB at idle/moderate load)
- Sustained limit: 550W per node (PDU safety margin)
- Hard limit (facility PDU threshold): 600W per node

## Breach response
1. Identify offending job via `slurm query_jobs`.
2. If sustained > 600W for >10 min: cancel job with `slurm scancel`.
3. File incident report with affected_resource and affected_job.

## GPU power capping
Run `nvidia-smi -pl <watts>` on the node to apply a software power cap.
Typical training cap: 400W per GPU (1600W per node for 4-GPU systems).
