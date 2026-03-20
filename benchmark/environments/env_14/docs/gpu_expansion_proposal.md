# GPU Expansion Proposal — Q3 2026

## Current state
- GPU nodes: 4 (gpu01–gpu04), each with 4× A100 80GB
- Total GPUs: 16
- 30-day average utilisation: 97%
- 30-day average queue wait: 18 hours

## Demand projection
- ML workload growth: ~15% month-over-month
- Projected demand at Q3 2026: equivalent of 28 A100s (175% of current)

## Expansion options
| Option | GPUs added | Cost | Lead time |
|--------|-----------|------|-----------|
| 2× A100 nodes (8 GPUs) | 8 | $320K | 8 weeks |
| 4× A100 nodes (16 GPUs) | 16 | $640K | 8 weeks |
| 4× H100 nodes (32 GPUs) | 32 (equiv) | $1.1M | 12 weeks |

## Recommendation
Option C (4× H100) provides 2× compute/GPU vs A100 for AI workloads,
effectively adding 64 A100-equivalent GPU slots. Covers projected demand
through Q1 2027.
