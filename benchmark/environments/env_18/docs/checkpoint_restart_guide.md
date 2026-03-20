# Checkpoint and Restart Guide

## Scratch filesystem purge policy
- `/scratch` files are automatically deleted after **30 days** without access.
- This is to prevent scratch from filling up.
- **Do NOT store checkpoints you intend to reuse in /scratch.**

## Where to store checkpoints
- Long-term: `/project/<group>/<user>/checkpoints/` (not purged, quota applies)
- Short-term (active jobs): `/scratch/<user>/` (purged after 30 days)

## Recovering from missing checkpoint
1. Check if checkpoint was saved to a non-scratch location.
2. If not: you must restart the simulation from the beginning.
3. Update your job script to write checkpoints to `/project/` going forward.

## Writing a restart-capable job script
```bash
#SBATCH --job-name=md_restart
CHECKPOINT=/project/phys-lab/alice/checkpoints/md_run.chk
if [ -f "$CHECKPOINT" ]; then
    srun md_sim --restart "$CHECKPOINT"
else
    srun md_sim --new-run
fi
```
