# Capacity Planning Guide — ExaBench Cluster C

## Utilization Thresholds
| Threshold | Action |
|---|---|
| > 80% sustained (30-day avg) | Trigger procurement process |
| > 90% peak | Emergency allocation review |
| < 40% (12-month avg) | Decommission review |

## Current Partition Status
| Partition | 30-day Utilization | Action Required |
|---|---|---|
| cpu_standard | 72% | Monitor |
| gpu_v100 | 91% | **Expansion in progress** (H100 procurement) |
| highmem | 63% | Monitor |

## GPU Expansion Plan
8x NVIDIA H100 80GB SXM5 nodes approved for 2026-Q3.
Estimated impact: gpu partition utilization drops to ~68% post-install.
Power requirement per node: 6.4 kW. Total new load: 51.2 kW.
Facility headroom available: 120 kW (60% of 200 kW budget).
