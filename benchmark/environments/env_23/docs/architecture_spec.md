# Cluster Architecture Specification — AOBench Cluster C

## Acceptance Test Criteria for New Nodes
New nodes must pass ALL of the following before entering production:

1. **BIOS/firmware verification**: Vendor-recommended firmware version installed
2. **Memory test**: `memtest86+` — zero errors over 2 passes
3. **CPU stress test**: `stress-ng --cpu 0 --timeout 3600s` — no thermal throttling
4. **Interconnect bandwidth**: InfiniBand bandwidth test >= 95% of rated line rate
5. **Storage I/O**: Node-local `fio` sequential read >= 3 GB/s (NVMe)
6. **GPU burn-in (GPU nodes)**: `gpu-burn` for 1 hour — no errors, max temp < 85°C
7. **Integration**: Node visible in SLURM, passes hello-world MPI job

## Network Architecture
Fat-tree topology with two HDR InfiniBand core switches (ib-core-01, ib-core-02) and 8 leaf switches. Blocking ratio 2:1 for compute, non-blocking for storage fabric.

## Storage Hierarchy
| Tier | System | Capacity | Purpose |
|---|---|---|---|
| Scratch | Lustre | 2.0 PB | Job I/O |
| Home | GPFS | 100 TB | User files |
| Archive | Spectrum Scale | 5 PB | Long-term |
