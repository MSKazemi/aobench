# Developer Guide

This page is a **developer-oriented map of the codebase**. It tells you which
file owns which responsibility, the conventions to follow when extending the
system, and where to look for examples.

For a complete component map and line-by-line module descriptions, see [System Architecture](../reference/system-architecture.md).

---

## 1. Code layout

```
src/exabench/
├── cli/             Typer app — `exabench` console script
├── schemas/         Pydantic v2 data models (no logic)
├── loaders/         Stateless task / env loading
├── tasks/           Task discovery, dataset splits, RAG context, Lite selection
├── validation/      T1–T10 validity-gate orchestrator
├── environment/     Snapshot validator + tool-registry factory
├── tools/           Mock HPC tool families + tool catalog
├── adapters/        Agent backends: direct_qa / openai / anthropic / mcp
├── runners/         BenchmarkRunner, TraceWriter, ExecutionContext
├── scorers/         12 scorers across 6 dimensions
├── scoring/         CuP gating + advanced scoring helpers
├── reports/         JSON, HTML, slice, CLEAR scorecard reports
├── exporters/       Optional observability (Langfuse)
├── leaderboard/     FastAPI submission service + DB models
├── reproducibility/ Artifact locking, paper-table targets, determinism check
├── judge/           LLM-judge runner + rubric loading
├── error_taxonomy/  HPC error classification
├── gym/             Gym-compatible wrapper (partial — see future-work plan §C3)
├── taxonomy/        24-leaf TRAIL-adapted error taxonomy YAML
└── utils/           Logging, ID generation, cost estimation
```

For each module, [System Architecture §2](../reference/system-architecture.md)
lists the public classes and functions. Use that as a quick reference.

---

## 2. The eight CLI sub-commands

The `exabench` console script is built with [Typer](https://typer.tiangolo.com/).
Its sub-commands are:

| Command | Module | Purpose |
|---------|--------|---------|
| `exabench validate benchmark` | `cli/validate_cmd.py` | Lint every task spec and snapshot bundle |
| `exabench run task` / `run all` | `cli/run_cmd.py` | Execute one task or the dev split |
| `exabench lite select` | `cli/lite_cmd.py` | Build the ExaBench-Lite manifest |
| `exabench report json/html/slices` | `cli/report_cmd.py` | Render reports from a run directory |
| `exabench compare RUN_A RUN_B` | `cli/compare_cmd.py` | Diff two runs |
| `exabench robustness task/all` | `cli/robustness_cmd.py` | Compute pass^k |
| `exabench clear run` | `cli/clear_cmd.py` | Compute the CLEAR scorecard |
| `exabench leaderboard` | `cli/leaderboard_cmd.py` | Start the FastAPI submission service |

The full reference, with every flag, is in [`COMMANDS.md`](../reference/commands.md).

---

## 3. Adding a new adapter

1. Subclass `BaseAdapter` in `adapters/base.py`. Implement
   `run(task, tools, ctx) -> Trace`.
2. Inside `run`, call `tools.dispatch(tool_name, args)` for each tool the
   agent invokes. The registry handles RBAC filtering and propagates
   `permission_denied` observations.
3. Append every step to the `TraceWriter` provided in the
   `ExecutionContext`. Finalise to obtain the `Trace`.
4. Register the adapter in the dispatch table in `cli/run_cmd.py`
   (`_ADAPTER_REGISTRY`). The CLI accepts `--adapter <name>:<model>`.
5. Add unit tests under `tests/unit/test_<name>_adapter.py`. Use the
   `mock_openai` / `mock_anthropic` fixtures as templates.

The four shipped adapters cover the typical interaction patterns:

| Adapter | Shape | Reference |
|---------|-------|-----------|
| `direct_qa` | Zero-tool baseline; returns the QA answer for the task ID | `adapters/direct_qa_adapter.py` |
| `openai` | OpenAI / Azure function-calling loop | `adapters/openai_adapter.py` |
| `anthropic` | Claude native `tool_use` blocks | `adapters/anthropic_adapter.py` |
| `mcp` | Model Context Protocol over stdio + SSE | `adapters/mcp_adapter.py` |

---

## 4. Adding a new mock tool

1. Subclass `BaseTool` in `tools/base.py`. Implement each public method as a
   pure function over the `EnvBundle`.
2. Register the tool's methods in `benchmark/configs/hpc_tool_catalog.yaml`,
   including `description`, `parameters`, `role_visibility`, and any
   `dangerous_args` conditions.
3. Update `environment/snapshot_loader.build_tool_registry` if the tool needs
   a new env-bundle field.
4. Add a sample invocation under each affected `env_NN/` bundle.
5. Tests under `tests/unit/test_<tool>_tool.py`.

RBAC is enforced inside the registry, not inside individual tools — keep
business logic in the tool, permission logic in `tools/registry.py`.

---

## 5. Adding a new scorer

1. Subclass `BaseScorer` in `scorers/base.py`. Implement
   `score(task, trace) -> ScorerOutput`.
2. Wire the scorer into `scorers/aggregate.py` if it should contribute to
   the aggregate score. Update `scoring_profiles.yaml` weights as needed.
3. If the scorer can hard-fail, populate `scorer_output.hard_fail_reason`;
   the aggregate scorer will force `aggregate_score = 0.0`.
4. Tests under `tests/unit/test_<scorer>_scorer.py` (deterministic) and
   `tests/integration/test_aggregate_scorer.py` (end-to-end).

The 12 implemented scorers and their wiring status are listed in
[System Architecture §7](../reference/system-architecture.md). Notes:

- `WorfEvalScorer` (`workflow_scorer.py`) is implemented but **not yet
  wired** into `AggregateScorer`. Wiring is tracked in the future-work plan
  (§A3).
- `CheckpointScorer` is wired conditionally (only when `task.checkpoints` is
  set). It contributes via `S_partial = 0.5 * (passed/total) + 0.5 * S_full`.
- `RobustnessScorer` is invoked only via the `exabench robustness` CLI; it is
  not part of the per-task aggregate.

---

## 6. Authoring a new task

End-to-end task authoring is described in
[Taxonomy §5 (Task Metadata Schema)](taxonomy.md). The minimum
acceptance criterion is that `exabench validate benchmark` succeeds with the
new task: that runs T1–T10 validity gates (covered in
`src/exabench/validation/`).

For programmatic task generation, see `scripts/create_task_stubs.py` and the
guideline files under `benchmark/tasks/guidelines/`.

The interactive `exabench task create` helper is part of the v0.2 plan (see
future-work plan §B1, `task_authoring_spec`).

---

## 7. Configuration files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, dependencies, console-script entry. Optional extras: `[openai]`, `[anthropic]`, `[mcp]`, `[langfuse]`. |
| `Makefile` | 40+ targets: `test`, `lint`, `typecheck`, `validate`, `paper-table*`, `rubric-validate-all`, `repro-table-1/2`, `langfuse-up/down`, `leaderboard-serve`. |
| `.env.example` | Template for `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LANGFUSE_*`, leaderboard DB URL. |
| `Dockerfile` | Reproducible runtime image. |
| `benchmark/configs/scoring_profiles.yaml` | Named weight profiles. |
| `benchmark/configs/hpc_tool_catalog.yaml` | All 16 tool methods, role visibility, dangerous-arg conditions. |
| `benchmark/configs/error_taxonomy.yaml` | 14 score-based error categories. |
| `benchmark/environments/env_NN/rbac_policy.yaml` | Per-env, per-role permissions (schema v1.1). |

---

## 8. Tests

`tests/` is split into `tests/unit/` (per-module) and
`tests/integration/` (end-to-end pipelines).

| Layer | Files | Examples |
|-------|-------|----------|
| Unit | 30 | `test_outcome_scorer.py`, `test_governance_scorer.py`, `test_snapshot_validator.py`, `test_task_loader.py` |
| Integration | 6 | `test_runner_e2e.py`, `test_clear_pipeline.py`, `test_checkpoint_pipeline.py` |

Run them via:

```bash
make test         # unit only, fast
make test-cov     # unit + integration with coverage
make validate     # validity gates over benchmark data
```

CI in `.github/workflows/ci.yml` runs `lint`, `typecheck`, `test`, and
`validate` on Python 3.12, 3.13, and 3.14.

---

## 9. Conventions

- **Pydantic v2 only.** Schemas live in `schemas/`; never inline ad-hoc
  dicts.
- **`BaseExporter` for observability.** Avoid coupling the runner to a
  specific backend.
- **Logging via `utils/logging.get_logger(__name__)`.** Do not call
  `print` from library code.
- **Cost estimation via `utils/cost.estimate_cost`.** Token counts come from
  adapter responses; do not infer.
- **Trace IDs come from `utils/ids.make_trace_id` and
  `make_run_id`.** They are stable across re-runs of the same task in the
  same run.

---

## 10. Reference

| Topic | Page |
|-------|------|
| Implemented architecture | [system-architecture.md](../reference/system-architecture.md) |
| CLI reference | [`COMMANDS.md`](../reference/commands.md) |
| Evaluation protocol | [evaluation.md](evaluation.md) |
| Scorer reference | [scoring-dimensions.md](scoring-dimensions.md) |
| Adapters & tools (plain English) | [`adapters-and-tools.md`](../guides/adapters-and-tools.md) |
| Architecture diagrams | [`system-architecture.md §12`](../reference/system-architecture.md) |
| How to Contribute | [`contributing.md`](../about/contributing.md) |
