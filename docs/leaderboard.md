---
title: "AOBench leaderboard — HPC agent benchmark results"
description: "Published AOBench results for AI agents on HPC operational tasks, the reference baselines, and how to submit your own reproducible run to the leaderboard."
keywords:
  - HPC agent leaderboard
  - LLM benchmark results
  - agent evaluation results
---

# Leaderboard

**A leaderboard is only as good as the reproducibility of its rows.** Every entry here
names its AOBench version, split, scoring profile, and exact model snapshot, so anyone
can re-derive it. Entries that cannot be re-derived do not go on the board.

## Reference baselines

These ship with the benchmark and anchor the scale. Reproduce them yourself with the
commands shown.

| Entry | Score | Version | Split | Profile | Reproduce |
|---|---:|---|---|---|---|
| `direct_qa` (tool-free floor), task `JOB_USR_001` | **0.334** | 0.4.1 | — | `default_hpc_v01` | `aobench quickstart` |

`direct_qa` calls no tools and answers from the prompt alone. It exists to give the
scale a floor: **any tool-using agent that does not clearly beat it is not using tools
usefully.** A score *below* the floor generally means the agent is calling tools badly
rather than not at all.

!!! note "Why this table is short"
    Model rows are added as runs are completed and verified against the submission
    requirements below. We would rather publish three rows anyone can reproduce than
    thirty nobody can. If you have run AOBench, **your submission is genuinely wanted** —
    including a bad result, which is often the more informative kind.

## Submitting a result

### 1. Run it

```bash
aobench run all --adapter <your adapter> --split dev
aobench clear run data/runs/<run_id>
aobench report json data/runs/<run_id>
```

`aobench report json` **writes** `data/runs/<run_id>/run_summary.json` and prints a short
human summary to the terminal. It does not emit JSON on stdout, so do not redirect it —
attach `run_summary.json` itself.

Use `--split dev`. Results on the locked `test` split are accepted only from
maintainers or by prior arrangement, because a public test-split leaderboard is a
training target within a year.

### 2. Check it meets the bar

A submission must state:

| Field | Example | Why |
|---|---|---|
| AOBench version | `0.4.1` | The corpus is part of the version |
| Split | `dev` | Scores differ by split |
| Scoring profile | `corpus default` | Weights change the aggregate — see below |
| Adapter | `openai` | How the agent was driven |
| Model snapshot | `gpt-4o-2024-11-20` | **Immutable**, never a moving alias |
| Judge model | `gpt-4o-2024-11-20` or `n/a` | Rubric-path variance |
| Runs | `3` | Single runs are not evidence |
| Hard fails | `0` | Reported separately from the score, always |
| Cost | `$4.20` | So others can budget a replication |
| Per-dimension scores | see below | Where the score was won or lost |

And it must be **re-derivable by someone else**: the adapter has to be either one that
ships with AOBench, a public MCP server, or a documented endpoint.

### The profile is per task, not per run

Each task spec names its own `aggregate_weight_profile`, so a full-split run mixes them:
on the current corpus, **60 tasks score under `alpha1_grounding` and 28 under
`default_hpc_v01`**. A dev-split run therefore has no single profile, and that is by
design — `alpha1_grounding` puts weight on grounding and tool use for tasks where gold
evidence exists, which is not meaningful for every task.

Write `corpus default` in that field unless you deliberately forced one profile across
every task, in which case say which and note that the number is not comparable to rows
that used the corpus default.

Confirm what your own run used with:

```bash
jq -r '.tasks[].weight_profile_name' data/runs/<run_id>/run_summary.json | sort | uniq -c
```

### Where to find the per-dimension scores

`aobench report json` writes `mean_dimension_scores` into the run summary — the
run-level mean for each of the **seven** weighted dimensions. Paste that object
straight into the submission:

```bash
jq .mean_dimension_scores data/runs/<run_id>/run_summary.json
```

```json
{
  "outcome": 0.7124, "tool_use": 0.6810, "grounding": 0.5903,
  "governance": 0.9500, "robustness": 0.4417, "efficiency": 0.8302,
  "workflow": 0.6188
}
```

!!! note "`null` is a valid value here — it means *not measured*, not zero"
    Two of the seven cannot be derived from a single pass over a single task, so a
    narrow run reports them as `null`:

    - **`robustness`** needs the *same* task run repeatedly, which is what
      `aobench robustness` does — a one-shot run has nothing to vary.
    - **`workflow`** compares the trace against a task's `ground_truth_workflow` and is
      `null` for tasks that do not define one.

    Verified on a single-task run:

    ```json
    {"outcome": 0.24, "tool_use": 0.0, "grounding": 0.0, "governance": 1.0,
     "robustness": null, "efficiency": 1.0, "workflow": null}
    ```

    **Report `null` as `n/a`, never as `0`.** Writing zero claims the agent scored nothing
    on a dimension that was never measured, which drags an aggregate that never included
    it. A full `--split dev` run populates `workflow` for the tasks that define one.

The same seven appear per task under `.tasks[]`, which is what to look at when one
dimension drags the aggregate down and you want to know which tasks did it. Each task row
also carries its own `weight_profile_name`, and `.weight_profiles` gives the run-level
tally, so the weights behind a row can always be recovered from the file alone.

!!! warning "In 0.4.1 and earlier the summary omitted `workflow`"
    `workflow` carries 0.10 weight in `default_hpc_v01`, but those versions of the run
    summary did not emit it, so a breakdown taken from such a file will not reconcile
    against the aggregate. Regenerate it with `aobench report json` on a build that
    includes this fix. The underlying result files always stored the value, so no
    re-run is needed.

### Reporting more than one run

The bar is three independent runs, and the form has one score field, so report the
**mean across runs** as the headline number and give the spread alongside it:

| Field | What to put |
|---|---|
| Aggregate score | Mean across your runs, e.g. `0.6192` |
| Number of independent runs | `3` |
| Anything notable | Per-run scores and the range, e.g. `0.611 / 0.619 / 0.628` |

Attach **every** run's `run_summary.json`, not just the one you took the headline from.
The spread is the part that says whether a gap between two agents is real, so a
submission with three attached runs is worth more to the board than a tidier single
number.

### 3. Submit

Open a [leaderboard submission issue](https://github.com/MSKazemi/aobench/issues/new/choose)
with `run_summary.json` attached and the table above filled in. Submissions are checked
for internal consistency and, where possible, spot-replicated before they go on the
board.

## Reading a leaderboard row honestly

Three habits worth having, including with our own numbers:

1. **Look at hard fails before the aggregate.** A high score with a non-zero hard-fail
   count is the dangerous profile: competent right up until it oversteps its role.
2. **Distrust small gaps.** With 67 dev tasks, differences under a couple of points are
   usually noise. Ask for the confidence interval.
3. **Check the profile.** An aggregate under a custom profile is not comparable to one
   under `default_hpc_v01`, however similar the number looks.

## Running your own private leaderboard

Nothing here requires our involvement. `aobench leaderboard` serves the same view over
your own runs, which is the right approach for evaluating vendor agents under NDA:

```bash
aobench serve rest             # then POST your runs
aobench leaderboard --help
```

The public board is a convenience, not the product. The reproducible evaluation is the
product.

---

**Related:** [versioning and comparability](about/versioning.md) ·
[reproducing results](about/reproducing-results.md) ·
[evaluate your own agent](guides/evaluating-your-own-agent.md)
