---
title: "Adding a task to the AOBench corpus"
description: "How to contribute a new HPC operational task to AOBench: the TaskSpec schema, choosing a role and QCAT, writing a gold trajectory, the fidelity gate, and the review checklist."
keywords:
  - contribute benchmark task
  - TaskSpec schema
  - HPC benchmark authoring
---

# Adding a task

**Corpus breadth is the main thing limiting what AOBench can measure, so a good new
task is the most valuable contribution to this project.** This page is the complete
path from idea to merged.

## Before you write anything

Ask three questions:

1. **Would a competent operator answer this differently depending on their role?** If
   not, it is probably a knowledge question rather than an operations task, and it
   belongs in `DOCS` at best.
2. **Is the answer derivable from an environment snapshot?** Every gold answer must be
   supported by evidence that actually exists in a bundle. If answering requires
   knowledge the agent has no way to obtain, the task measures memorisation.
3. **Does an existing environment support it, or do you need a new one?** Reusing an
   environment is much cheaper — check the
   [environment catalog](../reference/environment-catalog.md) first.

If you are unsure, open a
[task proposal issue](https://github.com/MSKazemi/aobench/issues/new/choose) before
writing. That costs you ten minutes and can save a day.

## Start with the scaffolder

You do not have to type the shape of a spec from memory:

```bash
aobench new task --thinnest        # fills the emptiest QCAT x role cell
aobench new task --cell DOCS_DES   # or choose the cell yourself
```

It allocates the next free task ID, picks an environment that comparable tasks already
use, and prints the files that exist in that snapshot so you can cite them without going
exploring. What it writes is valid from the first byte — but the `title`, `query_text` and
`gold_answer` are `TODO`, because those are the parts worth having a human write. A
generated gold answer would just measure the model that generated it.

Read the rest of this page while you fill those in; it explains what each field is for and
what a reviewer will check.

## The anatomy of a task spec

Task specs are JSON in `benchmark/tasks/specs/<TASK_ID>.json`, validated against the
`TaskSpec` Pydantic model in `src/aobench/schemas/task.py` — **that model, not this
page, is authoritative**.

### Naming

`<QCAT>_<ROLE_CODE>_<NNN>.json`, e.g. `JOB_USR_001`, `MON_SYS_004`, `ENERGY_FAC_002`.

| Role | Code |
|---|---|
| `scientific_user` | `USR` |
| `sysadmin` | `SYS` |
| `facility_admin` | `FAC` |
| `researcher` | `RES` |
| `system_designer` | `DES` |

Tasks grounded in Marconi100 data use the `M100_` prefix instead.

### The fields that matter most

```json
{
  "task_id": "JOB_USR_042",
  "title": "Diagnose an out-of-memory job failure",
  "qcat": "JOB",
  "role": "scientific_user",
  "environment_id": "env_01",
  "benchmark_split": "dev",
  "query_text": "My job 12345 died last night. What happened and what should I change?",
  "allowed_tools": ["slurm", "telemetry", "docs"],
  "expected_answer_type": "explanation",
  "gold_trajectory": { "...": "the ordered tool calls a competent operator makes" },
  "gold_evidence_refs": ["slurm/job_details.json#12345", "telemetry/memory_events.csv"],
  "eval_criteria": { "evaluation_mode": "rubric", "...": "..." },
  "hard_fail_conditions": ["..."],
  "difficulty_tier": 2,
  "contamination_risk": "low"
}
```

**`allowed_tools` is a permission statement, not a hint.** It says what this role may
use for this task. Tools outside it are what the governance dimension catches.

**`gold_evidence_refs` must point at facts that exist in the bundle.** The fidelity
gate checks this, and a task that fails it will not merge.

**`gold_trajectory` is a reference, not a straitjacket.** An agent that reaches the
right answer by a different reasonable route should not be heavily penalised; write the
trajectory a good operator would follow, not the only one you can imagine.

### Choosing a scoring mode

| Mode | Use when | Reproducibility |
|---|---|---|
| `deterministic` | The answer is a node ID, a job state, a number, or a set | Exact |
| `rubric` | The answer is an explanation or a recommendation | Judge variance |

**Prefer deterministic wherever the question allows it.** Every rubric task adds judge
variance to everyone's results forever. If you can rephrase "what happened?" as "which
node failed, and why?", do.

## The workflow

```bash
# 0. Scaffold it — picks the next free ID, suggests the environment comparable tasks use,
#    and lists the evidence files that actually exist in that snapshot.
aobench new task --cell JOB_USR          # or --thinnest to fill the emptiest cell

# 1. Write the parts that matter: the question, the gold answer, the evidence refs.
$EDITOR benchmark/tasks/specs/JOB_USR_042.json

# 2. Does it load and type-check?
aobench validate benchmark

# 3. Does it appear where you expect?
aobench list tasks --qcat JOB --role scientific_user

# 4. Does the tool-free baseline fail it? (It should — otherwise the task is trivial.)
aobench run task --task JOB_USR_042 --env env_01 --adapter direct_qa

# 5. Does a real agent pass it? (It should be possible — otherwise the task is broken.)
aobench run task --task JOB_USR_042 --env env_01 --adapter openai:gpt-4o

# 6. Regenerate the catalog page and run the suite
make catalog
uv run python -m pytest tests/
```

Step 4 and step 5 together are the discriminating-power check, and they catch most bad
tasks. A task that `direct_qa` passes is measuring nothing. A task that no agent can
pass is either broken or asking for information that is not in the bundle.

## The fidelity gate (F1–F7)

Every task and environment pair must pass internal-consistency checks: the anomaly the
task asks about must be present in the telemetry, the gold evidence must exist, the
role must be supported by the environment, the allowed tools must be available. Run
them with `aobench validate benchmark`.

`AOBENCH_SKIP_FIDELITY=1` bypasses the gate. The test suite sets it for speed. **Never
set it while authoring a task** — it is exactly the check you need.

## Splits

New tasks default to `dev`. Only maintainers move a task to `test`, and only when it
has been stable for a release, because the held-out split loses its value the moment it
churns.

## Review checklist

What a reviewer will check, so you can check it first:

- [ ] `aobench validate benchmark` passes
- [ ] The role could plausibly ask this question
- [ ] The answer is derivable from evidence in the named environment
- [ ] `allowed_tools` reflects the role's real permissions, not the task's convenience
- [ ] `direct_qa` does **not** pass it
- [ ] At least one real agent **can** pass it
- [ ] Deterministic scoring is used unless the question genuinely needs a rubric
- [ ] `make catalog` was run and the diff committed
- [ ] The task adds coverage rather than duplicating an existing one

## What happens next

You will get a first response within three working days, even if that response is
"seen, I'll look properly on Friday". Corpus PRs sometimes need a conversation about
whether the gold answer is right — that is a discussion about HPC operations, not a
criticism of your work, and it is the most interesting part of maintaining this project.
