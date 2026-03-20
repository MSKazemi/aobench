# MPI Job Failure Troubleshooting

## Common failure modes
1. **Network timeout**: One rank loses connectivity; other ranks hang waiting.
2. **OOM kill**: A rank exceeds memory limit and is killed.
3. **Node failure**: Hardware fault causes one node to drop out.
4. **Rank timeout**: Slow node causes MPI barrier timeout.

## Diagnosis steps for network timeout (exit 137)
1. Query telemetry: `telemetry query_timeseries metric_name=net_rx_mbps`
   — Look for zero or near-zero values on any node during the job runtime.
2. Check SLURM node state: nodes that failed should be drained.
3. On the suspect node: `ip link show` — check for link-down.
4. Check switch logs for port errors: `ethtool -S <nic>`.

## Network hardware checklist
- Check NIC link status: `ethtool eth0 | grep -i link`
- Check switch port: contact network admin for switch port counters
- Check InfiniBand (if used): `ibstat`, `ibdiagnet`
- Replace NIC or cable if persistent link failures confirmed
