# SLURM Configuration Guide

## Default partition
- Set `Default=YES` on exactly one partition.
- Jobs submitted without `-p` go to the default partition.
- Only one partition can be default; if multiple have `Default=YES`, behaviour is undefined.

## GPU partition configuration
- GPU partitions should NOT be the default.
- Users must explicitly request GPU resources with `-p gpu --gres=gpu:N`.
- Prevents CPU-only jobs from consuming GPU nodes.

## Verifying configuration after reload
1. `sinfo -o "%P %D %C"` — check partition status and node counts.
2. `scontrol show partition <name>` — verify Default=YES/NO.
3. Submit a test job without `-p` and verify it lands in 'standard'.

## Safe config reload procedure
1. Edit `/etc/slurm/slurm.conf`
2. `scontrol reconfig` (live reload, no restart needed)
3. Verify with `sinfo` immediately
