# AOBench

**Benchmark framework for evaluating AI agent systems in High-Performance Computing (HPC) environments.**

AOBench measures how well AI agents complete HPC operational tasks — job
scheduling, telemetry interpretation, energy reasoning, policy enforcement —
using the right tools, the right roles, and the right permissions. Instead of
running on live clusters, every task is evaluated against a deterministic
environment snapshot with mock HPC tools (SLURM, telemetry, RBAC, docs,
facility), so results are reproducible, portable, and safe to publish.



## Requirements

- **Python** ≥ 3.12
- Optional: `openai`, `anthropic`, or `mcp` Python clients to drive the
  corresponding adapters.

## Five benchmark principles

| Principle | Meaning |
|-----------|---------|
| **Role-aware** | The same question yields different answers and tool access depending on the requester role. |
| **Tool-using** | Agents are evaluated as systems that call HPC-native tools (SLURM, telemetry, docs, RBAC, facility). |
| **Permission-aware** | Success requires respecting RBAC and refusing out-of-scope requests. Permission violations hard-fail the task. |
| **Trace-based** | Evaluation considers the full execution trace — tool selection, arguments, sequence, and grounding — not just the final answer. |
| **Reproducible** | Runs target deterministic snapshot bundles, never live infrastructure. |

## Repository layout

```
AOBench/
├── src/aobench/           # Python package (installed by `pip install -e .`)
│   ├── cli/                # `aobench` typer app — 9 sub-commands
│   ├── schemas/            # Pydantic data models (task, trace, snapshot, …)
│   ├── loaders/, tasks/    # Task discovery, loading, dataset splits, RAG context
│   ├── environment/        # Snapshot validator, snapshot loader factory
│   ├── tools/              # Mock SLURM, telemetry, docs, RBAC, facility tools
│   ├── adapters/           # direct_qa, openai, anthropic, mcp
│   ├── runners/            # BenchmarkRunner, TraceWriter, ExecutionContext
│   ├── scorers/            # 12 scorers across 6 dimensions
│   ├── reports/            # JSON, HTML, slice, CLEAR scorecard reports
│   ├── exporters/          # Langfuse exporter (optional)
│   ├── leaderboard/        # FastAPI leaderboard service
│   ├── reproducibility/    # Artifact locking + paper-table targets
│   └── taxonomy/           # 24-leaf TRAIL-adapted HPC error taxonomy
│
├── benchmark/              # Static benchmark data (versioned in git)
│   ├── tasks/specs/        # 80 JSON task specs (all 10 QCATs × 5 roles)
│   ├── tasks/task_set_v1.json   # 36 HPC v1 tasks (Souza 2025 schema)
│   ├── tasks/task_set_v3.json   # v3 task index (80 tasks)
│   ├── tasks/dataset_splits.py  # 62 dev / 18 test split (~22% held-out)
│   ├── tasks/lite_manifest_v1.json  # AOBench-Lite curated subset
│   ├── environments/env_01–env_26/  # 26 deterministic snapshot bundles
│   ├── configs/            # scoring_profiles.yaml, hpc_tool_catalog.yaml,
│   │                       # error_taxonomy.yaml
│   └── qa/                 # AOBench-QA (~95 HPC operational queries)
│
├── data/                   # Generated artifacts
│   ├── runs/               # Per-run traces & results (gitignored)
│   ├── reports/            # Validity gate reports
│   ├── robustness/         # pass^k results
│   └── rubric_validation/  # Annotator profiles, response set, guides
│
├── prompts/judge/          # LLM-judge rubric + error taxonomy templates
├── docs/                   # Documentation (see Documentation section)
├── scripts/                # Bundle generation, validity gates, rubric tooling
└── tests/                  # 51 test files (unit + integration)
```

## Quick start

```bash
pip install -e ".[dev]"

# 1. Validate every task spec and environment bundle
aobench validate benchmark

# 2. Run one task end-to-end with the zero-tool baseline
aobench run task --task JOB_USR_001 --env env_01 --adapter direct_qa

# 3. Run a real adapter and emit a CLEAR scorecard
export OPENAI_API_KEY=sk-…
aobench run all --adapter openai:gpt-4o --split dev
aobench report json data/runs/<run_id>
aobench clear run data/runs/<run_id>
```

## Implemented scope (v0.3)

| Item | Count | Location |
|------|-------|----------|
| Tasks | 80 across 10 QCATs × 5 roles | `benchmark/tasks/specs/` |
| Environments | 26 deterministic snapshot bundles | `benchmark/environments/env_01`…`env_26` |
| Roles (scored) | 5 — `scientific_user`, `sysadmin`, `facility_admin`, `researcher`, `system_designer` | `src/aobench/schemas/task.py` |
| QCATs (scored) | 10 — `JOB`, `MON`, `ENERGY`, `PERF`, `DATA`, `SEC`, `FAC`, `ARCH`, `AIOPS`, `DOCS` | `benchmark/tasks/specs/` |
| Adapters | 4 — `direct_qa`, `openai`, `anthropic`, `mcp` | `src/aobench/adapters/` |
| Mock tool families | 5 — slurm, docs, rbac, telemetry, facility | `src/aobench/tools/` |
| Scorers | 12 across 6 dimensions | `src/aobench/scorers/` |
| Scoring profiles | `alpha0_minimal`, `alpha1_grounding`, `default_hpc_v01` | `benchmark/configs/scoring_profiles.yaml` |
| Tests | 1048 passing | `tests/` |

The 6 evaluation dimensions and their `default_hpc_v01` weights:

| Dimension | Weight | Scorer |
|-----------|--------|--------|
| Outcome correctness | 0.30 | `OutcomeScorer` (or `HybridScorer`) |
| Tool-use correctness | 0.20 | `ToolUseScorer` (BFCL-decomposed) |
| Governance / RBAC | 0.20 | `GovernanceScorer` |
| Grounding | 0.15 | `GroundingScorer` |
| Robustness (pass^k) | 0.10 | `RobustnessScorer` |
| Efficiency | 0.05 | `EfficiencyScorer` |

The CLEAR scorecard (`aobench clear run`) aggregates Efficacy, Assurance,
Reliability, Cost, and Latency into a single comparable score per model.

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/framework/index.md](docs/framework/index.md) | Documentation map |
| [docs/framework/system-architecture.md](docs/framework/system-architecture.md) | **Authoritative system architecture** — components, data flow, scoring pipeline, CLEAR scorecard |
| [docs/framework/overview.md](docs/framework/overview.md) | Principles and v0.1 scope |
| [docs/framework/background.md](docs/framework/background.md) | Motivation and related work |
| [docs/framework/architecture.md](docs/framework/architecture.md) | Benchmark design (layers, entities, workflow) |
| [docs/framework/implementation.md](docs/framework/implementation.md) | Developer guide to the codebase |
| [docs/framework/environments.md](docs/framework/environments.md) | Snapshot format |
| [docs/framework/evaluation.md](docs/framework/evaluation.md) | Evaluation protocol, trace and result schemas |
| [docs/framework/taxonomy.md](docs/framework/taxonomy.md) | Roles, QCATs, knowledge sources, RBAC |
| [docs/framework/scoring-dimensions.md](docs/framework/scoring-dimensions.md) | Per-scorer reference |
| [docs/COMMANDS.md](docs/reference/commands.md) | CLI command reference |
| [docs/environments-overview.md](docs/reference/environments-overview.md) | Inventory of all 20 environment bundles |
| [docs/adapters-and-tools.md](docs/guides/adapters-and-tools.md) | Plain-English adapter and tool guide |
| [docs/architecture-flowchart.md](docs/reference/architecture-flowchart.md) | System diagrams |
| [docs/langfuse-integration.md](docs/guides/langfuse-integration.md) | Observability backend |
| [docs/paper_reproduction_guide.md](docs/guides/paper-reproduction.md) | Reproducing v0.1 paper tables |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guide |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting and threat model |

## AOBench-QA

The `benchmark/qa/` directory embeds the AOBench-QA dataset — ~95 HPC
operational queries with role-specific variants and structured taxonomies. It
is consumed by the `direct_qa` baseline and seeds task design for the v1 HPC
task set.

## License

Apache 2.0 — see [LICENSE](LICENSE).
