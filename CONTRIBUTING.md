# Contributing to ExaBench

## Setup

```bash
git clone https://github.com/MSKazemi/ExaBench
cd ExaBench
make install        # creates .venv and installs all deps
make validate       # verifies benchmark data loads cleanly
make test           # 58 tests should pass
```

Requires [uv](https://github.com/astral-sh/uv). Python 3.11+.

---

## How to Add a Task

A task is a JSON file in `benchmark/tasks/specs/`. Every task must reference a real environment bundle and have a verified gold answer before it can be marked `scoring_readiness: ready`.

**Step 1 — Pick an environment.** Check which environments exist:

```bash
make coverage-matrix
ls benchmark/environments/
```

**Step 2 — Write the task spec.** Create `benchmark/tasks/specs/<TASK_ID>.json`:

```json
{
  "task_id": "JOB_USR_004",
  "title": "Short title",
  "query_text": "The exact question the agent will be asked.",
  "role": "scientific_user",
  "qcat": "JOB",
  "difficulty": "easy",
  "environment_id": "env_01",
  "gold_evidence_refs": ["slurm/job_details.json#oom_evidence"],
  "expected_answer_type": "diagnosis",
  "eval_criteria": {
    "evaluation_mode": "semantic_match",
    "gold_answer": "The exact correct answer derived from the environment data.",
    "required_evidence_refs": ["slurm/job_details.json#oom_evidence"]
  },
  "allowed_tools": ["slurm", "docs"],
  "hard_fail_conditions": [],
  "aggregate_weight_profile": "alpha1_grounding",
  "benchmark_split": "dev",
  "validation_status": "in_review",
  "scoring_readiness": "ready"
}
```

Valid values:
- `role`: `scientific_user` | `sysadmin` | `facility_admin`
- `qcat`: `JOB` | `MON` | `ENERGY`
- `difficulty`: `easy` | `medium` | `hard` | `adversarial`
- `evaluation_mode`: `semantic_match` | `exact_match` | `numeric_tolerance`
- `aggregate_weight_profile`: `alpha1_grounding` (recommended) | `alpha0_minimal` | `default_hpc_v01`
- `allowed_tools`: any subset of `["slurm", "docs", "rbac", "telemetry", "facility"]`

**Step 3 — Verify the gold answer** by reading the actual environment files in `benchmark/environments/<env_id>/`. The gold answer must be derivable from those files alone.

**Step 4 — Validate:**

```bash
make validate
uv run python scripts/check_coverage.py
```

**Step 5 — Run a baseline:**

```bash
make run TASK=JOB_USR_004 ENV=env_01 ADAPTER=direct_qa
```

---

## How to Add an Environment

An environment is a directory under `benchmark/environments/env_XX/` with deterministic snapshot data.

**Required files:**

```
env_XX/
  metadata.yaml      # environment_id, scenario_type, supported_roles, included_files, ...
  manifest.txt       # list of all data files (one per line)
  policy/
    rbac_policy.yaml # role permissions
```

**Optional data directories** (add whichever apply to your scenario):

| Directory | Contents |
|-----------|----------|
| `slurm/` | `slurm_state.json`, `job_details.json`, `pending_jobs.json`, `qos_limits.json` |
| `telemetry/` | `node_metrics.json`, `memory_events.csv`, `queue_pressure_metrics.csv` |
| `power/` | `node_power_*.csv`, `cluster_energy_*.csv`, `rack_energy_*.csv` |
| `rack/` | `rack_telemetry_*.csv` |
| `inventory/` | `node_map.csv`, `rack_layout.csv` |
| `docs/` | Markdown policy/guide files for the `docs` tool |
| `incidents/` | `incident_metadata.json` |
| `cooling/` | `crac_status.json` |
| `alerts/` | `node_alerts.json` |

See `benchmark/environments/env_01/` (simple) or `env_05/` (facility scenario) as templates.

Validate after creating: `make validate`

---

## How to Add an Adapter

An adapter wraps an LLM (or any agent) and translates ExaBench's `ExecutionContext` into a `Trace`.

**Step 1 — Create the adapter file:**

```python
# src/exabench/adapters/my_adapter.py
from exabench.adapters.base import BaseAdapter
from exabench.runners.context import ExecutionContext
from exabench.schemas.trace import Trace

class MyAdapter(BaseAdapter):
    name = "my_adapter"

    def run(self, context: ExecutionContext) -> Trace:
        # 1. Use context.task.query_text as the user prompt
        # 2. Use context.tools.call(tool_name, method, **kwargs) for tool calls
        # 3. Build and return a Trace with steps, final_answer, hard_fail, etc.
        ...
```

Key objects:
- `context.task` — `TaskSpec` (query, role, allowed_tools, gold_evidence_refs)
- `context.tools` — `ToolRegistry` (call tools, check permissions)
- `context.tools.available_tool_names` — list of tool names available for this task/role
- Return a `Trace` — see `src/exabench/schemas/trace.py`

**Step 2 — Register in `run_cmd.py`:**

```python
# src/exabench/cli/run_cmd.py  — _build_adapter()
if name == "my_adapter":
    from exabench.adapters.my_adapter import MyAdapter
    return MyAdapter()
```

**Step 3 — Add OpenAI-style tool schemas** (if the adapter uses function calling):

Add your tool's JSON schema to `src/exabench/adapters/openai_adapter.py:_TOOL_SCHEMAS` — or generate it from the tool class if it exposes a `schema()` method.

**Step 4 — Test:**

```bash
make run TASK=JOB_USR_001 ENV=env_01 ADAPTER=my_adapter
```

---

## How to Add a Scorer

A scorer evaluates one dimension of agent quality from a `TaskSpec` and `Trace`.

```python
# src/exabench/scorers/my_scorer.py
from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace
from exabench.scorers.base import BaseScorer, ScorerOutput

class MyScorer(BaseScorer):
    dimension = "my_dimension"

    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        if trace.hard_fail:
            return ScorerOutput(dimension=self.dimension, score=0.0,
                                hard_fail=True, hard_fail_reason=trace.hard_fail_reason)
        score = ...  # compute 0.0–1.0
        return ScorerOutput(dimension=self.dimension, score=score, notes="...")
```

Register in `src/exabench/scorers/aggregate.py:_SCORERS` and add the dimension to `DimensionScores` in `src/exabench/schemas/result.py`. Add a weight entry to each profile in `benchmark/configs/scoring_profiles.yaml`.

Write tests in `tests/unit/test_my_scorer.py`.

---

## Code Standards

- Python 3.11+, Pydantic v2, Typer CLI
- `uv run ruff check src/ tests/` must pass (no errors)
- `uv run mypy src/exabench/` must pass
- Every new module needs at least basic unit tests
- Run `make check` before opening a PR

## Branch and PR Conventions

- Branch from `main`, name: `feature/<topic>` or `fix/<topic>`
- Each PR should do one thing
- The CI workflow (`.github/workflows/ci.yml`) must pass
