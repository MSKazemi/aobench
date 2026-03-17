# ExaBench

**Benchmark framework for evaluating AI agent systems in High-Performance Computing (HPC) environments.**

ExaBench measures how well AI agents can complete HPC operational tasks using the right tools, roles, and permissions. Instead of testing on live clusters, it uses deterministic environment snapshots and mock HPC tools (SLURM, telemetry, RBAC, docs) so evaluation is reproducible and safe.

## Requirements

- **Python** 3.10+
- Optional: `openai` or `anthropic` for LLM-based adapters

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
    └── framework/          # Framework design documents (01–07)
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

## Implementation Status

ExaBench is under active development. The roadmap describes three phases:

- **Phase 1** — Minimal executable benchmark: task/environment loaders, mock tools (SLURM, docs, RBAC), one adapter, runner, trace writer, and core scorers
- **Phase 2** — Stronger benchmark: telemetry tool, grounding/tool-use scorers, HTML reports, role × category slicing
- **Phase 3** — Advanced extensions: robustness variants, facility/energy tools, MCP compatibility, API service

See [docs/roadmap.md](docs/roadmap.md) for details.

## v0.1 Scope

- **Tasks**: ~30 (3 categories: JOB, MON, ENERGY)
- **Environments**: ~5 deterministic HPC snapshots
- **Roles**: `scientific_user`, `sysadmin`, `facility_admin`
- **Baselines**: `direct_qa`, `rag_baseline`, `tool_agent_baseline`

## ExaBench-QA

The `benchmark/qa/` directory contains the ExaBench-QA query dataset — ~95 HPC operational queries with role-specific variants, taxonomies, and schemas. Queries cover job scheduling, monitoring, energy, and policy topics across multiple roles. Data is stored in CSV, JSON, and Markdown formats in `benchmark/qa/data/queries/`.

## Documentation

| Document | Description |
|----------|-------------|
| [Framework Index](docs/framework/index.md) | Document map and quick links |
| [01 Overview](docs/framework/01-overview.md) | Principles, v0.1 scope, single source of truth |
| [03 Architecture](docs/framework/03-architecture.md) | Benchmark design: layers, entities, workflow |
| [04 Implementation](docs/framework/04-implementation.md) | Software architecture, CLI, adapters |
| [05 Environments](docs/framework/05-environments.md) | Environment snapshot format |
| [06 Evaluation](docs/framework/06-evaluation.md) | Metrics, trace schema, scoring |
| [07 Taxonomy](docs/framework/07-taxonomy.md) | Roles, categories, access control |
| [Roadmap](docs/roadmap.md) | Implementation phases and milestones |

## License

Apache 2.0 — see [LICENSE](LICENSE).
