# ExaBench

**Benchmark framework for evaluating AI agent systems in High-Performance Computing (HPC) environments.**

ExaBench evaluates whether an AI agent can operate reliably, safely, and efficiently in HPC environments under realistic tool, role, and policy constraints.

## Five Benchmark Principles

| Principle | Description |
|---|---|
| **Role-Aware** | The same question yields different answers and tool access depending on requester role |
| **Tool-Using** | Agents are evaluated as systems using HPC-native tools (SLURM, telemetry, docs, RBAC) |
| **Permission-Aware** | Success requires respecting RBAC boundaries and refusing out-of-scope requests |
| **Trace-Based** | Evaluation considers the full execution trace, not just the final answer |
| **Reproducible** | Evaluation runs against deterministic environment snapshots, not live infrastructure |

## Repository Structure

```
ExaBench/
├── src/exabench/           # Python package (pip install exabench)
│   ├── schemas/            # Pydantic data models
│   ├── loaders/            # Task and environment loaders
│   ├── tools/              # Mock HPC tools (SLURM, telemetry, docs, RBAC)
│   ├── adapters/           # Agent backend adapters
│   ├── runners/            # Execution runner and trace writer
│   ├── scorers/            # Scoring engine (outcome, governance, efficiency)
│   └── cli/                # exabench run / validate commands
│
├── benchmark/              # Benchmark dataset (static source data)
│   ├── tasks/specs/        # Task specification files (JSON)
│   ├── environments/       # HPC state snapshot bundles
│   ├── configs/            # Scoring profiles, tool registry
│   └── qa/                 # ExaBench-QA dataset (query corpus)
│
├── data/runs/              # Runtime artifacts (traces, results — gitignored)
├── tests/                  # Unit and integration tests
└── docs/                   # Documentation
    └── framework/          # Framework design documents (00–08)
```

## Quick Start

```bash
pip install -e ".[dev]"

# Validate all benchmark data
exabench validate benchmark

# Run a task
exabench run task --task JOB_USR_001 --env env_01 --adapter direct_qa
```

## Evaluation Dimensions

| Dimension | Weight (v0.1) | Description |
|---|---|---|
| Outcome Correctness | 30% | Task answered correctly |
| Tool-Use Correctness | 20% | Right tools, arguments, sequences |
| Grounding Quality | 15% | Answer supported by valid evidence |
| Governance Compliance | 20% | RBAC, refusal, redaction correctness |
| Robustness | 10% | Consistency across repeated runs |
| Efficiency | 5% | Latency, token usage, step count |

## v0.1 Scope

- **Tasks**: ~30 (3 categories: JOB, MON, ENERGY)
- **Environments**: ~5 deterministic HPC snapshots
- **Roles**: `scientific_user`, `sysadmin`, `facility_admin`
- **Baselines**: `direct_qa`, `rag_baseline`, `tool_agent_baseline`

## ExaBench-QA

The `benchmark/qa/` directory contains the ExaBench-QA query dataset — ~95 HPC operational queries with role-specific variants, taxonomies, and schemas. See [benchmark/qa/README.md](benchmark/qa/README.md) for details.

## License

Apache 2.0 — see [LICENSE](LICENSE).
