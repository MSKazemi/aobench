# Contributing to AOBench

## Setup

```bash
git clone https://github.com/MSKazemi/aobench
cd aobench
make install        # creates .venv and installs all deps
make validate       # verifies benchmark data loads cleanly
make test           # ~1510 tests should pass
```

Requires [uv](https://github.com/astral-sh/uv). Python 3.11+.

If `make` is unavailable, the equivalent commands are:

```bash
uv sync --all-extras
uv run aobench validate benchmark
uv run python -m pytest tests/
```

These are the same commands CI runs. Before opening a PR, also run:

```bash
uv run ruff check src tests scripts
uv run ruff format src tests          # scripts/ is lint-gated but not format-gated
uv run mypy src/aobench       # advisory — not all findings block a PR
```

---

## What to expect from us

- **First response within 3 working days.** A first response may just be "seen,
  I'll look properly on Friday" — that still counts, and you will get one.
- If a PR of yours goes quiet for more than a week, ping it. That is a
  maintainer failure, not rudeness on your part.
- **Prefer PRs under ~300 changed lines.** Larger work is welcome, but open an
  issue first so we can agree the approach before you write it.
- **Open an issue before starting** anything that changes the task schema, the
  scoring weights, the RBAC model, or a public CLI signature. Bug fixes, docs,
  tests, examples and new CLI flags need no prior discussion — just send them.
- **If an issue turns out to be already done, say so.** It happens — three of ours
  were. Flagging it is a real contribution and gets credited in `AUTHORS.md`; it is
  never something you should feel awkward about raising.
- **CI does not run on your first PR until a maintainer approves it.** GitHub
  holds workflow runs on pull requests from first-time contributors, so
  `gh pr checks` says *"no checks reported"* and the PR page shows nothing at
  all. That is not a failure and not something you can fix from your side —
  it means we have not pressed the button yet. Ping the PR if it stays that way.

---

## Using AI assistance

**AI assistance is welcome.** We are not going to ask how you wrote your code, and
"you used an LLM" is not a rejection reason here — it would be a strange one in a
project about evaluating AI agents.

What we do ask is the same thing we would ask of any contributor:

- **You understand the change and can explain it in review.** If a reviewer asks
  "why this approach rather than X?", you should be able to answer.
- **You have run the tests locally.** `make check`, not "it looked right".
- **You take responsibility for it.** Your name is on the PR.
- **Please disclose substantial AI assistance in the PR description.** It costs you
  nothing, it is not held against you, and it helps us review well.

If you are pointing a coding agent at this repository,
[`AGENTS.md`](https://github.com/MSKazemi/aobench/blob/main/AGENTS.md) is
written for it — architecture, commands, invariants, and what must not be changed.
Point the agent there first.

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

An adapter wraps an LLM (or any agent) and translates AOBench's `ExecutionContext` into a `Trace`.

**Step 1 — Create the adapter file:**

```python
# src/aobench/adapters/my_adapter.py
from aobench.adapters.base import BaseAdapter
from aobench.runners.context import ExecutionContext
from aobench.schemas.trace import Trace

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
- Return a `Trace` — see `src/aobench/schemas/trace.py`

**Step 2 — Register in `run_cmd.py`:**

```python
# src/aobench/cli/run_cmd.py  — _build_adapter()
if name == "my_adapter":
    from aobench.adapters.my_adapter import MyAdapter
    return MyAdapter()
```

**Step 3 — Add OpenAI-style tool schemas** (if the adapter uses function calling):

Add your tool's JSON schema to `src/aobench/adapters/openai_adapter.py:_TOOL_SCHEMAS` — or generate it from the tool class if it exposes a `schema()` method.

**Step 4 — Test:**

```bash
make run TASK=JOB_USR_001 ENV=env_01 ADAPTER=my_adapter
```

---

## How to Add a Scorer

A scorer evaluates one dimension of agent quality from a `TaskSpec` and `Trace`.

```python
# src/aobench/scorers/my_scorer.py
from aobench.schemas.task import TaskSpec
from aobench.schemas.trace import Trace
from aobench.scorers.base import BaseScorer, ScorerOutput

class MyScorer(BaseScorer):
    dimension = "my_dimension"

    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        if trace.hard_fail:
            return ScorerOutput(dimension=self.dimension, score=0.0,
                                hard_fail=True, hard_fail_reason=trace.hard_fail_reason)
        score = ...  # compute 0.0–1.0
        return ScorerOutput(dimension=self.dimension, score=score, notes="...")
```

Register in `src/aobench/scorers/aggregate.py:_SCORERS` and add the dimension to `DimensionScores` in `src/aobench/schemas/result.py`. Add a weight entry to each profile in `benchmark/configs/scoring_profiles.yaml`.

Write tests in `tests/unit/test_my_scorer.py`.

---

## Code Standards

- Python 3.10+ (3.12 in CI and Docker), Pydantic v2, Typer CLI
- `uv run ruff check src/ tests/ scripts/` must pass (no errors)
- Every new module needs at least basic unit tests
- Run `make check` before opening a PR — it is green on `main`, so anything it
  reports is yours

### Type checking

**`uv run mypy src/aobench/` does not pass, and you are not expected to make it
pass.** `--strict` still reports pre-existing debt in 8 of 25 packages. Do not
try to clear it as a side effect of your PR, and do not add `# type: ignore` to
quieten something you did not touch.

The gate is a **ratchet**, not a clean tree:

```bash
make typecheck-ratchet      # the real gate — also part of `make check`
make typecheck              # advisory: the full list, debt included
```

It fails only when debt *grows* — a package listed in `mypy_baseline.json` may
not exceed its budget, and any package absent from that file must stay at zero.
Seventeen packages are already at zero and are held there.

**If you pay debt down, the ratchet also fails** — deliberately, because an
unrecorded improvement is a budget nobody ever lowers. It prints the one command
that records it:

```bash
make typecheck-accept       # updates mypy_baseline.json — commit that file
```

That is good news, not a problem with your PR.

### Silent exception handlers

`make check` also fails on a **new** broad `except` that does not surface the failure —
one whose body is `pass`, or only logs below WARNING, or returns a plausible value like
`None`/`False`/`[]`:

```bash
make silent-handlers-check     # part of `make check`
make silent-handlers-accept    # record a reviewed handler — commit the baseline file
```

This is not a style rule. Six defects in this codebase have shared exactly that shape: a
real error caught and turned into a valid-looking result, so nothing raised and no test
went red. The gym environment reported every tool call as forbidden; the Langfuse
exporter dropped the session ID from every trace; the fidelity gate passed a corrupt
bundle; the leaderboard quietly dropped result files it could not read.

Broad handlers are sometimes right, and ten of them are recorded in
`silent_handlers_baseline.json` for that reason. If yours is one of them, accept it
deliberately and say why in the PR. Before you do, check it cannot hide a change in
something you do not control — a third-party API, a file format, an attribute name.
That is how all six survived.

A handler that returns a *failed* result carrying the error — the pattern in the F1–F7
fidelity validators and the T1–T10 checks — is not flagged, because it surfaces the
failure to whoever reads the report.

## Editing the Documentation Site

The site under `docs/` is MkDocs Material, published to
<https://mskazemi.com/aobench/>. Two things about it have caught contributors
out, and neither is your fault if it does:

**1. Links are relative to the page's own directory, not to `docs/`.**
From `docs/getting-started/first-10-minutes.md`, the sibling install page is
`installation.md` — *not* `getting-started/installation.md`, which resolves to
`docs/getting-started/getting-started/installation.md` and breaks the build. To
reach another directory, go up: `../guides/adapters-and-tools.md`,
`../leaderboard.md`.

**2. A new page must be added to `nav:` in `mkdocs.yml`.** Without it the page
builds but nothing links to it, so nobody will ever find it.

Both are caught by the same command, which is what CI runs:

```bash
uv run mkdocs build --strict    # broken links and orphan pages fail the build
uv run mkdocs serve             # live preview at http://127.0.0.1:8000
```

**Check any command you document by running it.** Several pages have drifted
from the CLI over time; `aobench --help` and `aobench <cmd> --help` are the
authority, and run output belongs in the page as the CLI actually prints it.

---

## Branch and PR Conventions

- Branch from `main`, name: `feature/<topic>` or `fix/<topic>`
- Each PR should do one thing
- The CI workflow (`.github/workflows/ci.yml`) must pass

## License

**There is nothing to sign.** No CLA, no DCO sign-off line, no `git commit -s`, no box to
tick, no account to create, and nothing for an employer's legal team to review. Opening the
pull request is the whole contract.

Apache-2.0 already grants the licence, in section 5:

> Unless You explicitly state otherwise, any Contribution intentionally submitted for
> inclusion in the Work by You to the Licensor shall be under the terms and conditions of
> this License, without any additional terms or conditions.

A sign-off would re-certify what the licence has already done, at the cost of a red check on
somebody's first pull request. Nothing checks for one, so there is nothing you can get wrong.

**You keep the copyright in your work.** AOBench is Apache-2.0 and stays that way.
