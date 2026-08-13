# AOBench Command Reference

Reference for all AOBench CLI commands and Makefile targets.

## Quick Reference

| Command | Description |
|---------|-------------|
| `aobench quickstart` | **Start here.** Run one scored task with no arguments and no API key |
| `aobench doctor` | Check the install: Python, corpus, extras, credentials — with a fix per failure |
| `aobench info` | Version, corpus location, extras, env vars (`--json` for bug reports) |
| `aobench list tasks` | List task IDs, filterable by `--qcat` / `--role` / `--split` / `--env` |
| `aobench list envs` | List environment bundles and their grounding |
| `aobench list qcats` \| `roles` \| `adapters` \| `profiles` \| `scorers` | Other views over the corpus |
| `aobench list coverage` | QCAT x role task-count matrix, with thin cells called out |
| `aobench validate benchmark` | Validate all task specs and environment bundles |
| `aobench run task` | Run a single benchmark task against an environment |
| `aobench run all` | Run all benchmark tasks (one run dir, one trace per task) |
| `aobench report json` | Write a JSON summary of all results in a run directory |
| `aobench report html` | Write a self-contained HTML benchmark report |
| `aobench report slices` | Print a role × category score table for a run |
| `aobench compare runs` | Diff two run directories — show score deltas and regressions |
| `aobench rescore` | Re-score an existing run's stored traces through the current scorer (no model calls) |
| `aobench robustness task` | Run a task N times and report score variance (robustness score) |
| `aobench robustness all` | Run ALL tasks N times each and report suite-level pass^k |
| `aobench clear run` | Compute CLEAR (Cost/Latency/Efficacy/Assurance/Reliability) scorecard |
| `aobench lite select` | Run 3-stage AOBench-Lite selection and write `benchmark/tasks/lite_manifest_v1.json` |
| `aobench serve rest` | Start the REST API (FastAPI) exposing the benchmark engine over HTTP (`rest` extra) |
| `aobench serve mcp` | Start the FastMCP server over stdio, exposing the engine as MCP tools/resources (`mcp` extra) |
| `aobench validate tasks` | Run T1–T10 validity checks with a human-readable pass/fail summary table |
| `aobench validate snapshots` | Run F1–F7 fidelity validators on all `env_*/` bundles; write `data/fidelity/` |
| `make quickstart` | Check the install, then run one scored task (no API key needed) |
| `make doctor` | Diagnose the install |
| `make install` | Install the dev group **and** all optional extras |
| `make install-dev` | Install the dev group only (pytest, ruff, mypy) |
| `make install-core` | Install just enough to run the benchmark |
| `make lite-select` | Run Lite selection pipeline (Stages 1–3) and write the Lite manifest |
| `make generate-tool-docs` | Write `hpc_tools_guide.md` into all env `docs/` dirs from `hpc_tool_catalog.yaml` |
| `make validate-tasks` | Run T1–T10 task validity checks on `benchmark/tasks/task_set_v1.json` |
| `make validate-snapshots` | Run F1–F7 fidelity validators on all `env_*/` snapshot bundles |
| `make validity-report` | Run T1–T10 task validity checks and write `benchmark/validity_report_v1.json` |
| `make audit-scorers` | Run O.a–O.c scorer validity audit and write `benchmark/scorer_audit_v1.json` |
| `make oracle-check` | Check that each task's gold answer is derivable from snapshot data |
| `make independence-check` | Detect near-duplicate tasks by cosine similarity of feature vectors |
| `make generate-rbac-docs` | Generate `docs/rbac_policy.md` for all 23 environment bundles |
| `make create-task-stubs` | Create minimal stub evidence files for oracle-check failures |
| `make leaderboard LEADERBOARD_RESULTS=<dir>` | Build CLEAR leaderboard from `<dir>/<model>/*.json` result files |
| `make check-validity-gates` | Run V0–V6 pre-publication validity gates and write `data/reports/validity_gates.json` (V0 = fidelity precondition, warning-only in v0.2) |
| `aobench validate authoring` | Run oracle_check and independence_check on all tasks |
| `python -m aobench.cli.validate_tasks` | Run T1–T10 ABC validity checklist against the task corpus |
| `python -m aobench.cli.audit_scorers` | Run O.a–O.c outcome validity audit against the scorer |
| `make rubric-generate-responses` | Generate 50 synthetic HPC validation responses in `data/rubric_validation/responses/` |
| `make rubric-compute-icc` | Compute ICC(A,1) from annotation CSV (Gate R1) |
| `make rubric-compute-krippendorff` | Compute Krippendorff α per rubric dimension (Gate R2) |
| `make rubric-stochastic-stability` | Run judge 8× on 10 responses, report stochastic std (Gate R3) |
| `make rubric-cross-judge` | Score 50 responses with two judges, report Kendall τ_b (Gate R4) |
| `make rubric-validate-all` | Run all 4 rubric validation gates (R1–R4) in sequence |
| `make paper-table1` | Generate Table 1 (main results) from `data/runs/v01_dev_*` summaries |
| `make paper-table4` | Generate Table 4 (pass^k reliability) from `data/robustness/v01_*.json` |
| `make check-validity-gates` | Run V1–V6 pre-publication validity gates and write `data/reports/validity_gates.json` |

---

## Getting started

### `aobench quickstart`

Run one benchmark task end-to-end and explain the result. Takes no arguments: it
resolves the benchmark corpus, picks a representative task, runs it with the tool-free
`direct_qa` adapter, prints the per-dimension scorecard, and names the next commands.
No API key, no network, and no cluster are required.

```bash
aobench quickstart                       # zero-argument first run
aobench quickstart --task MON_SYS_001    # a task you choose
aobench quickstart --adapter openai:gpt-4o   # a real model (needs a key)
aobench quickstart --output /tmp/runs    # write the run elsewhere
```

### `aobench doctor`

Diagnose the installation. Checks the Python version, that the package metadata is
readable, that the core dependencies import, that the benchmark corpus resolves and is
non-empty, and which optional extras are installed. Every failure prints a suggested fix.

Exits **1** only when a *required* check fails. Missing optional extras are warnings and
exit 0, because the `direct_qa` baseline needs none of them. Pass `--strict` to fail on
those warnings too — useful in CI that expects a full install.

```bash
aobench doctor
aobench doctor --strict
```

### `aobench info`

Print the version, corpus location and size, optional-extra status, and the relevant
environment variables. `--json` emits the same content as a machine-readable blob; that
is the thing to paste into a bug report.

```bash
aobench info
aobench info --json
```

### `aobench list`

Discover what is in the corpus without reading JSON by hand. Every sub-command accepts
`--json`; `list tasks` and `list envs` also accept `--ids-only` for shell pipelines.

```bash
aobench list tasks                       # all 88 tasks
aobench list tasks --qcat JOB --role sysadmin
aobench list tasks --split dev --ids-only
aobench list tasks --grounded            # only real-Marconi100 tasks
aobench list envs --grounded             # the 6 ExaData-grounded bundles
aobench list qcats                       # the 10 categories, with task counts
aobench list roles                       # the 5 operator roles, with task counts
aobench list adapters                    # what you can evaluate, and what each needs
aobench list profiles                    # scoring weight profiles and their weights
aobench list scorers                     # the scorers behind each dimension
aobench list coverage                    # QCAT x role task counts, and the thin cells
```

`list coverage` answers "where is the corpus thin, and how much of it is real hardware
data?" — the two questions you need before writing a task or citing a result:

- The **main matrix** counts every task once, from the spec's own `qcat`/`role` fields.
  Its total is always the size of the corpus; a task whose `qcat` or `role` is not one of
  the documented ten or five widens the matrix with its own row or column rather than
  going uncounted. (Whether such a value is *legal* is a question for
  `aobench validate benchmark` — `list` only reports what is there.)
- **Thin cells** hold at most one task, so a single spec carries the whole cell. **Empty
  cells** hold none at all and are listed separately when any exist; they are a subset of
  the thin ones, not an addition to them.
- The **M100-grounded table** is a *subset* of the main matrix, not an addition to it —
  those tasks are counted in both. It shows how much of any cell rests on real Marconi100
  ExaData rather than a synthetic snapshot.

Thin cells are where a contribution helps most — see
[issue #26](https://github.com/MSKazemi/aobench/issues/26).

```bash
# Pipe IDs straight into a loop
for t in $(aobench list tasks --qcat SEC --ids-only); do
  aobench run task --task "$t" --env env_01 --adapter direct_qa
done
```

### Locating the benchmark corpus

Every command that reads the corpus resolves it in this order: `$AOBENCH_BENCHMARK_ROOT`,
then a `benchmark/` directory found by walking up from the current directory, then the
copy bundled inside the installed package. `--benchmark /path/to/benchmark` overrides it
for one invocation. A mistyped `--task` or `--env` prints the closest matching IDs
instead of a traceback.

---

## CLI Commands

### Main

```bash
aobench [OPTIONS] COMMAND [ARGS]...
```

**Options:**

| Option | Description |
|--------|-------------|
| `--install-completion` | Install shell completion (bash, zsh, etc.) |
| `--show-completion` | Show completion script for manual setup |
| `-h`, `--help` | Show help and exit |

---

### validate

Validate benchmark data.

```bash
aobench validate [OPTIONS] COMMAND [ARGS]...
```

#### validate benchmark

Validate all task specs and environment bundles under a benchmark root.

```bash
aobench validate benchmark [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--benchmark` | `benchmark` | Path to benchmark root directory |
| `-h`, `--help` | — | Show help and exit |

**Example:**

```bash
aobench validate benchmark
aobench validate benchmark --benchmark /path/to/my-benchmark
```

#### validate snapshots

Run F1–F7 fidelity validators on all `env_*/` snapshot bundles under
`benchmark/environments/`. Writes per-environment Markdown reports and an
aggregate `REPORT.md` + `index.json` to the output directory.

```bash
aobench validate snapshots [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--environments` | `benchmark/environments` | Root directory containing `env_*/` bundles |
| `--output` / `-o` | `data/fidelity` | Output directory for Markdown reports and index |
| `-h`, `--help` | — | Show help and exit |

**Output files:**

| File | Description |
|------|-------------|
| `data/fidelity/<env_id>.md` | Per-environment F1–F7 report |
| `data/fidelity/REPORT.md` | Aggregate report across all environments |
| `data/fidelity/index.json` | JSON index: `[{env_id, passed, generated_at}]` |

**Example:**

```bash
aobench validate snapshots
aobench validate snapshots --environments benchmark/environments --output data/fidelity
make validate-snapshots
```

**Fidelity validators:**

| ID | Name | What it checks |
|----|------|----------------|
| F1 | Job-duration log-normal fit | `log(elapsed)` μ∈[6.3,9.3], σ∈[1.4,2.4] |
| F2 | Job-size power-law | CPU count power-law α∈[1.4,2.0] |
| F3 | Job-state mix | COMPLETED∈[68%,88%], FAILED∈[0%,19%] |
| F4 | Node power per class | CPU nodes 297–402 W; GPU nodes 1572–2128 W |
| F5 | Telemetry cadence | power CSVs 48–72s; state/energy 240–360s |
| F6 | RBAC completeness | Roles include `scientific_user` and `sysadmin` |
| F7 | Tool catalog coverage | All catalog methods have non-empty descriptions |

---

### validate_tasks (standalone script)

Run the full T1–T10 ABC validity checklist against the HPC task corpus.

```bash
python -m aobench.cli.validate_tasks [OPTIONS] [TASK_IDS...]
```

| Option | Default | Description |
|--------|---------|-------------|
| `TASK_IDS` | all | Optional task IDs to validate |
| `--task-file` | `benchmark/tasks/task_set_v1.json` | Task corpus JSON |
| `--snapshot-dir` | `benchmark/environments/` | Environments root directory |
| `--catalog` | `benchmark/configs/hpc_tool_catalog.yaml` | Tool catalog YAML |
| `--checks` | `all` | Comma-separated checks to run: `t1,t2,...,t9` |
| `--output` | stdout | Output report path |
| `--format` | `json` | Output format: `json` \| `text` \| `csv` |
| `--fail-fast` | false | Stop after first task failure |
| `--oracle-judge` | false | Run LLM oracle judge for rubric tasks |
| `--strict` | false | Treat WARN as FAIL |

**Examples:**

```bash
# Validate all tasks, all checks
python -m aobench.cli.validate_tasks

# Only run version and setup checks
python -m aobench.cli.validate_tasks --checks t1,t2

# Validate specific tasks, human-readable output
python -m aobench.cli.validate_tasks job_ops_01 job_ops_02 --format text

# Write validity report for release gate
make validity-report
# → benchmark/validity_report_v1.json
```

---

### audit_scorers (standalone script)

Run O.a–O.c outcome validity checks against the AOBench scorer.

```bash
python -m aobench.cli.audit_scorers [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--check` | `all` | Which check(s) to run: `oa` \| `ob` \| `oc` \| `all` |
| `--task-file` | `benchmark/tasks/task_set_v1.json` | Task corpus JSON |
| `--snapshot-dir` | `benchmark/environments/` | Environments root directory |
| `--judge-model` | `claude-sonnet-4-6` | LLM judge model for O.c |
| `--n-repeats` | `5` | Repeats per response for O.c stochastic test |
| `--output` | stdout | Output report path |
| `--format` | `json` | Output format: `json` \| `text` |
| `--string-equiv-file` | `benchmark/scorer_audit/string_equiv_classes.yaml` | Equivalence class YAML for O.a |

**Examples:**

```bash
# Run all checks
python -m aobench.cli.audit_scorers

# String-matching audit only
python -m aobench.cli.audit_scorers --check oa

# Rigorous self-consistency test
python -m aobench.cli.audit_scorers --check oc --n-repeats 10

# Write scorer audit report for release gate
make audit-scorers
# → benchmark/scorer_audit_v1.json
```

---

### run

Run benchmark tasks.

```bash
aobench run [OPTIONS] COMMAND [ARGS]...
```

#### run task

Run a single benchmark task against an environment.

```bash
aobench run task [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--task` | `-t` | (required) | Task ID, e.g. `JOB_USR_001` |
| `--env` | `-e` | (required) | Environment ID, e.g. `env_01` |
| `--adapter` | `-a` | `direct_qa` | Adapter name |
| `--benchmark` | — | `benchmark` | Path to benchmark root |
| `--output` | `-o` | `data/runs` | Output directory for runs |
| `--report/--no-report` | — | `--report` | Auto-generate JSON + HTML reports after run |
| `--langfuse/--no-langfuse` | — | `--no-langfuse` | Export trace and scores to Langfuse |
| `--verbose` | `-v` | off | Enable DEBUG logging to stderr |
| `-h`, `--help` | — | — | Show help and exit |

**Adapters:**

| Adapter | Description |
|---------|-------------|
| `direct_qa` | Direct question-answering (no LLM, parametric only) |
| `openai` | OpenAI API (default model: `gpt-4o`) |
| `openai:MODEL` | OpenAI with specific model, e.g. `openai:gpt-4o-mini` |
| `anthropic` | Anthropic Claude (default model: `claude-sonnet-4-6`) |
| `anthropic:MODEL` | Anthropic with specific model, e.g. `anthropic:claude-opus-4-6` |
| `mcp:stdio:COMMAND` | MCP client — launch a local subprocess via stdio transport |
| `mcp:sse:URL` | MCP client — connect to a remote MCP server via HTTP SSE |

**Required env vars per adapter:**

| Adapter | Env var |
|---------|---------|
| `openai` | `OPENAI_API_KEY` |
| `openai` (Azure) | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_DEPLOYMENT` |
| `anthropic` | `ANTHROPIC_API_KEY` |

**Langfuse env vars (required when `--langfuse` is set):**

| Env var | Required | Default | Description |
|---------|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | Yes | — | Project public key from Langfuse UI |
| `LANGFUSE_SECRET_KEY` | Yes | — | Project secret key from Langfuse UI |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Override for self-hosted instance |

**Examples:**

```bash
# Run with direct_qa adapter (default)
aobench run task --task JOB_USR_001 --env env_01

# Run with OpenAI
aobench run task -t JOB_USR_001 -e env_01 -a openai:gpt-4o

# Run with Anthropic Claude
aobench run task -t JOB_USR_001 -e env_01 -a anthropic:claude-sonnet-4-6

# Run via a local MCP server subprocess
aobench run task -t JOB_USR_001 -e env_01 -a "mcp:stdio:python my_agent.py"

# Run via a remote MCP server (SSE)
aobench run task -t JOB_USR_001 -e env_01 -a "mcp:sse:http://localhost:8000/sse"

# Custom benchmark path and output
aobench run task -t JOB_USR_001 -e env_01 -o results/

# Skip report generation
aobench run task -t JOB_USR_001 -e env_01 --no-report

# Enable DEBUG logging
aobench run task -t JOB_USR_001 -e env_01 --verbose

# Export to Langfuse (requires LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY)
aobench run task -t JOB_USR_001 -e env_01 --langfuse

# Export to self-hosted Langfuse
LANGFUSE_HOST=http://localhost:3000 aobench run task -t JOB_USR_001 -e env_01 --langfuse
```

#### run all

Run all benchmark tasks. Uses each task's `environment_id` from its spec. Creates one run directory with a trace and result file for every task. Displays a `rich` progress bar showing the current task ID, overall progress %, elapsed time, and last score.

```bash
aobench run all [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--adapter` | `-a` | `direct_qa` | Adapter name |
| `--benchmark` | — | `benchmark` | Path to benchmark root |
| `--output` | `-o` | `data/runs` | Output directory for runs |
| `--split` | `-s` | `all` | Task split to run: `all` \| `dev` \| `lite` \| `test` |
| `--report/--no-report` | — | `--report` | Auto-generate JSON + HTML reports after run |
| `--langfuse/--no-langfuse` | — | `--no-langfuse` | Export traces and scores to Langfuse |
| `--verbose` | `-v` | off | Enable DEBUG logging to stderr |
| `-h`, `--help` | — | — | Show help and exit |

**Split values:**

| Split | Description |
|-------|-------------|
| `all` | All tasks in `benchmark/tasks/specs/` (default) |
| `dev` | All tasks except `TEST_TASK_IDS` (70% dev split) |
| `lite` | Tasks in `LITE_TASK_IDS` from `lite_manifest_v1.json` |
| `test` | **Locked** — raises an error (held-out split, see `task_lite_spec.md §4.4`) |

**Output structure:** One run directory (e.g. `data/runs/run_20260318_123456_abc123/`) containing:

- `traces/<task_id>_trace.json` — one trace per task
- `results/<task_id>_result.json` — one result per task

**Examples:**

```bash
aobench run all
aobench run all --adapter openai:gpt-4o
aobench run all --adapter anthropic:claude-sonnet-4-6 --split lite
aobench run all --adapter openai:gpt-4o --split dev
aobench run all -o my_runs/
aobench run all --no-report   # skip report generation
aobench run all --adapter openai:gpt-4o --langfuse   # export all traces to Langfuse
```

---

### report

Generate reports from a completed benchmark run directory.

```bash
aobench report [OPTIONS] COMMAND [ARGS]...
```

Every `report` subcommand validates `RUN_DIR` before doing any work. If the path does not
exist, the command names it and lists up to ten sibling run directories. If it exists but
holds no completed result files, the command says so separately and prints an offline
re-run command. Both cases exit with code 2 and print no traceback.

#### report json

Write a JSON summary of all results in a run directory.

```bash
aobench report json [OPTIONS] RUN_DIR
```

| Argument / Option | Short | Default | Description |
|-------------------|-------|---------|-------------|
| `RUN_DIR` | | (required) | Path to run directory, e.g. `data/runs/run_…` |
| `--output` | `-o` | `<run_dir>/run_summary.json` | Output file path |
| `--json` | | `False` | Emit JSON instead of a table. Prints the summary dict to stdout with no banner and no human-readable lines — the file is still written as usual. Useful for wiring into CI. |
| `-h`, `--help` | | | Show help and exit |

**Output file:** `run_summary.json` with:
- `run_id`, `task_count`, `mean_aggregate_score`, `hard_fail_count`
- `total_cost_usd`, `total_tokens`, `mean_latency_seconds`
- `error_taxonomy` — counts per HPC error category (see below)
- `tasks` — per-task rows with all dimension scores, `error_category`, `cost_estimate_usd`, `latency_seconds`

**HPC error categories** (`error_category` field per task):

| Category | Meaning |
|----------|---------|
| `ok` | Correct, grounded, policy-compliant answer |
| `rbac_hard_fail` | Agent called a tool outside its role's permission boundary |
| `hard_fail` | Other hard-fail (max rounds, adapter error, etc.) |
| `no_tools_used` | Agent answered without calling any tools |
| `wrong_tool_sequence` | Called tools but wrong selection or order |
| `rbac_violation` | Soft RBAC failure — disclosed restricted info |
| `role_scope_error` | Answer scope wrong for the user's role |
| `ungrounded_answer` | Answer not traceable to tool observations |
| `energy_unit_or_value_error` | Had energy data but made unit/aggregation error |
| `job_misdiagnosis` | Had SLURM data but wrong failure diagnosis |
| `telemetry_interpretation_error` | Had telemetry but misread metric or node |
| `wrong_answer` | Clearly wrong, no domain-specific match |
| `partial` | Partially correct, below OK threshold |

Full category definitions and detection heuristics: `benchmark/configs/error_taxonomy.yaml`.

**Example:**

```bash
aobench report json data/runs/run_20260318_135249_14013e8c
aobench report json data/runs/run_20260318_135249_14013e8c -o reports/summary.json
aobench report json data/runs/run_20260318_135249_14013e8c --json | jq '.mean_aggregate_score'
```

#### report slices

Print a role × category score table to stdout.

```bash
aobench report slices [OPTIONS] RUN_DIR
```

| Argument  | Description                                      |
|-----------|--------------------------------------------------|
| `RUN_DIR` | Path to run directory, e.g. `data/runs/run_DATE` |

**Example:**

```bash
aobench report slices data/runs/run_20260318_135249_14013e8c
```

**Output:**

```text
Role × Category scores  (run: run_20260318_135249_14013e8c)

Role                        ENERGY           JOB           MON
--------------------------------------------------------------
facility_admin         0.618 (n=3)             -             -
scientific_user                  -   0.670 (n=3)             -
sysadmin                         -   0.610 (n=1)   0.620 (n=3)
```

#### report html

Write a self-contained HTML report for a run directory.

```bash
aobench report html RUN_DIR
```

**Example:**

```bash
aobench report html data/runs/run_20260318_143040_6a47e0f0
# Output: data/runs/run_20260318_143040_6a47e0f0/report.html
```

---

### compare

Compare two benchmark run directories.

```bash
aobench compare [OPTIONS] COMMAND [ARGS]...
```

#### compare runs

Show score deltas between two runs (run_b minus run_a). Positive delta = improvement.

```bash
aobench compare runs [OPTIONS] RUN_A RUN_B
```

| Argument | Description |
|----------|-------------|
| `RUN_A`  | Baseline run directory |
| `RUN_B`  | Comparison run directory |
| `--output` / `-o` | Optional path to write diff JSON |
| `--json` | Emit JSON instead of a table. Prints the same diff object to stdout with no banner and no tables — nothing else. Combine with `--output` to get both a file and stdout JSON. |

**Example:**

```bash
aobench compare runs data/runs/run_20260318_130835_abc data/runs/run_20260318_143040_def
aobench compare runs data/runs/run_20260318_130835_abc data/runs/run_20260318_143040_def --json | jq '.summary'
```

**JSON shape (`--json`, and the `--output` file):** the same object either way. Top level
carries `run_a` / `run_b`, `mean_score_a` / `mean_score_b` / `mean_delta`, `task_count_a` /
`task_count_b`, `hard_fail_count_a` / `hard_fail_count_b`, the applied filters
(`filter_qcat`, `filter_role`, `delta_threshold`), per-task `tasks[]` (each with `status`,
`score_a`, `score_b`, `delta`, `dim_deltas`, `hard_fail_changed`), a `summary` block of
counts (`improved`, `regressed`, `unchanged`, `new`, `removed`, `new_hard_fails`,
`resolved_hard_fails`), and `slices_a` / `slices_b` role×QCAT tables.

To gate CI on governance, key on the absolute count rather than the delta — a run can hold
its hard-fail total steady while swapping which tasks violate RBAC:

```bash
test "$(aobench compare runs "$BASE" "$NEW" --json | jq '.hard_fail_count_b')" -eq 0
```

**Output:**

```text
Baseline : run_20260318_130835_abc
Compare  : run_20260318_143040_def
Mean score: 0.6119 → 0.6334  (+0.0215)

Task                 Status        Score A  Score B    Delta
------------------------------------------------------------
ENERGY_FAC_001       ▲ improved     0.6119   0.6334  +0.0215
JOB_USR_001          = unchanged    0.7500   0.7500  +0.0000
...
Improved: 1  Regressed: 0  Unchanged: 9
```

---

### robustness

Measure score consistency across repeated runs.

```bash
aobench robustness [OPTIONS] COMMAND [ARGS]...
```

#### robustness task

Run a task N times with the same adapter and report score variance.

```bash
aobench robustness task [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--task` | `-t` | (required) | Task ID, e.g. `JOB_USR_001` |
| `--env` | `-e` | (required) | Environment ID, e.g. `env_01` |
| `--adapter` | `-a` | `direct_qa` | Adapter name |
| `--n` | | `5` | Number of repeated runs |
| `--output` | `-o` | | Optional path to write robustness JSON |
| `--benchmark-root` | | `benchmark` | Benchmark root directory |
| `--output-root` | | `data/runs` | Run output root directory |

**Output:** `robustness_score = 1.0 − std_dev`. A score of 1.0 means perfectly consistent results. Scores below 1.0 indicate the adapter produces variable answers for identical queries.

**Example:**

```bash
aobench robustness task --task JOB_USR_001 --env env_01 --adapter openai:gpt-4o --n 8
```

**Output:**

```text
Robustness run: JOB_USR_001 @ env_01  adapter=openai:gpt-4o  n=8

  Run 1/8  score=0.8124
  ...

──────────────────────────────────────────────────
Task         : JOB_USR_001
Runs         : 8  (passing: 7)
Threshold    : 0.5

pass^k (τ-bench reliability metric):
  pass^1   0.8750  █████████████████
  pass^2   0.7500  ███████████████
  pass^4   0.4286  ████████
  pass^8   0.0000

Mean score   : 0.7983
Std dev      : 0.0124
Range        : 0.7891 – 0.8124
Robustness   : 0.9876  (1 − σ)
──────────────────────────────────────────────────
```

#### robustness all

Run ALL benchmark tasks N times each and produce a suite-level pass^k report.

```bash
aobench robustness all [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--adapter` | `-a` | `direct_qa` | Adapter name (same format as `run task`) |
| `--n` | | `8` | Runs per task (≥ 8 recommended) |
| `--pass-threshold` | | `0.5` | Min aggregate_score to count a run as passing |
| `--split` | | (all) | Only run tasks in this split (`all`, `dev`, `lite`, `test`) |
| `--output` | `-o` | `data/runs/robustness_suite.json` | Write suite JSON to this path |
| `--benchmark-root` | | `benchmark` | Benchmark root directory |
| `--output-root` | | `data/runs` | Run output root directory |

**Example:**

```bash
# Quick smoke-test on dev split (4 runs each)
aobench robustness all --adapter direct_qa --n 4 --split dev

# Full reliability run for the paper (all 30 tasks × 8 runs)
aobench robustness all --adapter openai:gpt-4o --n 8
```

**Output:** A suite summary printed to stdout and written to `data/runs/robustness_suite.json` (or `--output`). Includes per-task pass^k, mean pass^k across all tasks, total cost, and mean latency.

---

### lite

AOBench-Lite subset selection commands. Implements the 3-stage pipeline from `task_lite_spec.md`:
Stage 1 (T1–T10 gate + split exclusion) → Stage 2 (attribute filter) → Stage 3 (execution filter).

```bash
aobench lite [OPTIONS] COMMAND [ARGS]...
```

#### lite select

Run the full 3-stage Lite selection pipeline and write `benchmark/tasks/lite_manifest_v1.json`.

```bash
aobench lite select [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--task-dir` | `benchmark/tasks/specs` | Task specs directory |
| `--pilot-scores` | — | JSON file with pilot scores `{task_id: {model: score}}` |
| `--output` | `benchmark/tasks/lite_manifest_v1.json` | Output manifest path |
| `--task-file` | `benchmark/tasks/task_set_v1.json` | Task corpus for T1–T10 validation |
| `--snapshot-dir` | `benchmark/environments/` | Environments directory |
| `--catalog` | `benchmark/configs/hpc_tool_catalog.yaml` | Tool catalog YAML |
| `--skip-validation` | off | Skip T1–T10 checks (use `task.t1_t10_pass` field) |

**Examples:**

```bash
# Stage 1+2 only (Stage 3 pending — no pilot scores yet)
aobench lite select

# Full 3-stage with pilot scores
aobench lite select --pilot-scores data/runs/v01_dev_gpt4o_mini/run_summary.json

# Custom paths
aobench lite select \
  --task-dir benchmark/tasks/specs \
  --pilot-scores data/pilot_scores.json \
  --output benchmark/tasks/lite_manifest_v2.json
```

**Makefile shortcut:**

```bash
make lite-select
make lite-select-with-scores PILOT_SCORES=data/runs/v01/run_summary.json
```

---

### clear

Compute the CLEAR multi-dimensional scorecard (Mehta 2025, arXiv:2511.14136) across one or more run directories.

CLEAR = **C**ost · **L**atency · **E**fficacy · **A**ssurance · **R**eliability

```bash
aobench clear run [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--run-dir` | `-d` | (required, repeatable) | Run directory containing `results/` (repeat for multiple models) |
| `--output` | `-o` | `clear_report.json` | Write CLEAR report JSON to this file |
| `--pass-threshold` | | `0.5` | Min `aggregate_score` to count a run as passing |
| `--reliability-k` | | `1` | k for pass^k reliability (1, 2, 4, 8) |
| `--robustness-json` | | | Optional: `robustness_suite.json` for pre-computed pass^k |

**CLEAR dimensions:**

| Symbol | Dimension | AOBench field | Notes |
|--------|-----------|----------------|-------|
| C | Cost | `cost_estimate_usd` | Min-max normalised across models; lower=better |
| L | Latency | `latency_seconds` | Min-max normalised across models; lower=better |
| E | Efficacy | `dimension_scores.outcome` | Mean outcome score (0–1) |
| A | Assurance | `dimension_scores.governance` | Engagement-aware: mean governance over runs that engaged a tool (`tool_use`>0); `None` when the model never engages. Legacy binary RBAC-compliance rate kept as `governance_v01` |
| R | Reliability | `pass^k` | Mean pass^k across tasks; uses `--reliability-k` |

**CLEAR composite:** `CLEAR = 0.2×C + 0.2×L + 0.2×E + 0.2×A + 0.2×R`

**Additional metrics per model:**

| Metric | Formula | Notes |
|--------|---------|-------|
| CNA | `(outcome / cost_usd) × 100` | Cost-Normalised Accuracy; higher=better |
| CPS | `total_cost / n_successful` | Cost Per Success; lower=better; None if 0 successes |

**Output JSON structure:**

```json
{
  "generated_at": "<ISO-8601>",
  "task_count": 30,
  "pass_threshold": 0.5,
  "reliability_k": 1,
  "models": {
    "gpt-4o": {
      "clear_score": 0.74, "C_norm": 0.82, "L_norm": 0.91,
      "E": 0.71, "A": 0.85, "R": 0.68,
      "mean_cost_usd": 0.0077, "mean_latency_s": 8.3,
      "CNA": 92.2, "CPS": 0.0089,
      "n_tasks": 30, "n_successful": 22
    }
  },
  "leaderboard": [
    {"rank": 1, "model": "gpt-4o", "clear_score": 0.74, "CNA": 92.2}
  ]
}
```

**Recommended workflow:**

```bash
# Step 1: single full run
aobench run all --adapter openai:gpt-4o

# Step 2: robustness run (for pass^8 reliability)
aobench robustness all --adapter openai:gpt-4o --n 8 \
    --output data/robustness_gpt4o.json

# Step 3: CLEAR scorecard
aobench clear run \
    --run-dir data/runs/run_20260319_<id>/ \
    --robustness-json data/robustness_gpt4o.json \
    --reliability-k 8 \
    --output data/clear_report.json

# Multi-model comparison (two run dirs, no robustness — uses pass^1)
aobench clear run \
    --run-dir data/runs/run_gpt4o/ \
    --run-dir data/runs/run_claude/ \
    --output data/clear_report_comparison.json
```

**Example stdout output:**

```text
Loaded 30 result(s) across 2 model(s).

Model                   CLEAR       E       A       R   C_norm   L_norm         CNA      CPS($)
──────────────────────────────────────────────────────────────────────────────────────────────
gpt-4o                  0.740   0.710   0.850   0.680    0.820    0.910       92.2    0.0089
claude-sonnet           0.718   0.695   0.890   0.650    0.760    0.880       89.1    0.0104

Tasks: 30  pass_threshold: 0.5  reliability_k: 1
CLEAR report written: data/clear_report.json
```

---

### rescore

Re-score an existing run's stored traces through the **current** `AggregateScorer`, without
re-invoking any model. Use this to recompute scores after a scorer change or bug fix (e.g. the
governance `tool__method` normalization) on runs you already have on disk.

```bash
aobench rescore RUN_DIR [OPTIONS]
```

| Argument / Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `RUN_DIR` | | (required) | Existing run directory containing `traces/*_trace.json` |
| `--output` | `-o` | (required) | Output directory; fresh `results/*_result.json` are written under it |
| `--benchmark-root` | | `benchmark` | Root holding `tasks/specs/` + `configs/scoring_profiles.yaml` |
| `--dry-run` | | `false` | Validate inputs and count traces without scoring |

Each `traces/<task_id>_trace.json` is reloaded, matched to its `TaskSpec`, replayed through the full
scorer stack, and written as a serialized `BenchmarkResult`. No agent or judge calls are made.

```bash
# Recompute scores for a stored run under the current scorer logic
aobench rescore data/runs/<run_id> -o data/runs/<run_id>_rescored
```

> For a governance-only re-score with an old-vs-new mean + Wilson CI comparison against the paper
> numbers, see the standalone `scripts/rescore_governance.py`.

---

### serve

Start an access server that exposes the benchmark **engine** for programmatic use.
Both transports call the shared `BenchmarkService` façade, so scores are identical
to the CLI — the transport carries no scoring logic. See the
[Programmatic access guide](../guides/programmatic-access.md) and
[serving tutorial](../tutorials/serving-the-benchmark.md) for end-to-end walkthroughs.

```bash
aobench serve rest [OPTIONS]     # REST API over HTTP
aobench serve mcp                # FastMCP server over stdio
```

**`serve rest` options** (requires `uv sync --extra rest`):

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Bind host |
| `--port` | `8000` | Bind port |

**`serve mcp`** (requires `uv sync --extra mcp`) runs over stdio for an MCP client to spawn.

**REST endpoints** (all under `/v1`):

| Method + path | Purpose |
|---------------|---------|
| `GET /v1/tasks`, `GET /v1/envs` | List task specs / environment bundles |
| `GET /v1/datasets` | List dataset versions + per-split task counts |
| `POST /v1/runs` | Run a task; `?wait=false` enqueues async and returns a job |
| `GET /v1/runs/{id}` | Fetch a run result |
| `GET /v1/runs/{id}/events` | **SSE** stream of run progress |
| `GET /v1/runs/{id}/report`, `/trace` | Run report / raw trace |
| `POST /v1/score` | Score a supplied trace against a task |
| `POST /v1/compare` | Diff two runs |
| `POST /v1/robustness` | Run a task N times (pass^k) |
| `GET /v1/jobs`, `GET /v1/jobs/{id}` | List / fetch async jobs |

Auth is API-key→role (header `X-API-Key`) with per-role rate limiting; unauthenticated
access maps to a read-only role.

**MCP tools:** `run_task`, `score_trace`, `validate_benchmark`, `robustness`.
**MCP resources:** `aobench://tasks`, `aobench://tasks/{id}`, `aobench://envs`,
`aobench://runs/{id}/report`, `aobench://runs/{id}/trace`.

**Examples:**

```bash
# REST API on all interfaces, port 9000
aobench serve rest --host 0.0.0.0 --port 9000

# then, from another shell:
curl -s localhost:9000/v1/tasks | jq '.[0]'
curl -s -X POST localhost:9000/v1/runs \
    -H 'Content-Type: application/json' \
    -d '{"task_id":"JOB_USR_001","env_id":"env_01","adapter":"direct_qa"}' | jq .clear
# async submission + poll
curl -s -X POST 'localhost:9000/v1/runs?wait=false' \
    -H 'Content-Type: application/json' \
    -d '{"task_id":"JOB_USR_001","env_id":"env_01","adapter":"direct_qa"}' | jq .job_id
curl -s localhost:9000/v1/jobs | jq .

# FastMCP server over stdio (an MCP client launches this command)
aobench serve mcp
```

---

## HPC Task Set v1

`benchmark/tasks/task_set_v1.json` contains 36 role-aware HPC observability tasks derived from Souza et al. (SC Workshops 2025, arXiv:2509.13978). Tasks span 6 data types, 2 workload classes, and 5 roles with per-role expected answers.

### Task distribution

| Data type | OLAP | OLTP | Total | Scoring |
|-----------|------|------|-------|---------|
| `job_ops` | 5 | 3 | 8 | 7 det / 1 rubric |
| `node_ops` | 4 | 2 | 6 | 5 det / 1 rubric |
| `telemetry` | 5 | 3 | 8 | 6 det / 2 rubric |
| `energy` | 5 | 2 | 7 | 5 det / 2 rubric |
| `dataflow` | 2 | 2 | 4 | 3 det / 1 rubric |
| `rbac` | 1 | 2 | 3 | 1 det / 2 rubric |
| **Total** | **22** | **14** | **36** | **27 det / 9 rubric** |

### Python API

```python
from aobench.tasks.task_loader import load_hpc_task_set, load_hpc_task
from aobench.tasks.context_builder import HPCContextBuilder

# Load all 36 tasks
tasks = load_hpc_task_set("benchmark/tasks/task_set_v1.json")

# Load a single task by ID
task = load_hpc_task("telemetry_04", "benchmark/tasks/task_set_v1.json")

# Build a 5-component RAG context bundle for a specific role
builder = HPCContextBuilder(guidelines_dir="benchmark/tasks/guidelines")
bundle = builder.build(task, role="sysadmin", snapshot_summary={})
# bundle keys: role_prompt, dynamic_schema, guidelines, few_shot_examples, question
```

### Validate

```bash
make validate-hpc-tasks
# HPC task set v1: 36 tasks loaded OK
#   dataflow: 4
#   energy: 7
#   job_ops: 8
#   node_ops: 6
#   rbac: 3
#   telemetry: 8
```

### Guidelines

Query guidelines live in `benchmark/tasks/guidelines/` — one file per data type. These give agents domain rules (job states, units, primary keys, partition names, RBAC tier definitions) and provide the largest per-token accuracy gain (see paper §6.3).

| File | Data type |
|------|-----------|
| `job_ops_guidelines.md` | SLURM job lifecycle queries |
| `node_ops_guidelines.md` | Node state and availability queries |
| `telemetry_guidelines.md` | CPU/GPU/memory/network metric queries |
| `energy_guidelines.md` | Power, energy, and efficiency queries |
| `dataflow_guidelines.md` | Data provenance and lineage queries |
| `rbac_guidelines.md` | Role-based access control and policy queries |

---

## Scoring Dimensions

AOBench scores every run on six dimensions.  See `docs/framework/scoring-dimensions.md`
for full definitions.  Quick reference:

| Dimension | What it measures | Scorer |
|-----------|-----------------|--------|
| `outcome` | Final answer correctness | `OutcomeScorer` |
| `tool_use` | Tool call quality (see below) | `ToolUseScorer` |
| `grounding` | Answer backed by retrieved evidence | `GroundingScorer` |
| `governance` | RBAC / policy compliance | `GovernanceScorer` |
| `efficiency` | Step and token economy | `EfficiencyScorer` |
| `robustness` | Consistency across repeated runs | `compute_robustness()` |

### `tool_use` sub-scores

**Decomposed mode** (requires `eval_criteria.expected_tool_sequence` in the task spec):

| Sub-score | Meaning |
|-----------|---------|
| `selection_score` | Did the agent call the right tools? (fraction of expected tools that were called) |
| `argument_score` | Were the arguments correct? (fraction of required arg key-value pairs that matched) |
| `sequence_score` | Did the agent call tools in the right order? (LCS of actual vs expected tool-name sequence) |
| `forbidden_call_penalty` | Did the agent avoid calling tools outside its allowed set? (1.0 − 0.3 per forbidden call) |

**Legacy mode** (when no `expected_tool_sequence` is set):

| Sub-score | Meaning |
|-----------|---------|
| `coverage` | Called at least one tool relevant to each evidence reference |
| `precision` | Avoided tools outside `allowed_tools` |
| `no_redundancy` | Avoided repeating the same call more than twice |

**Diagnostic coverage metrics** (appended to `ScorerOutput.notes`, not factored into the score):

| Metric | Formula | Source |
|--------|---------|--------|
| `tool_discovery_rate` | `\|tools called\| / \|tools available for role\|` | `hpc_tool_catalog.yaml` |
| `method_discovery_rate` | `\|(tool,method) pairs called\| / \|(tool,method) pairs available for role\|` | `hpc_tool_catalog.yaml` |

To add ground-truth tool sequences to a task, set `eval_criteria.expected_tool_sequence`:

```json
"eval_criteria": {
  "expected_tool_sequence": [
    {"tool_name": "slurm",   "required_args": {"method": "job_details", "job_id": "891234"}},
    {"tool_name": "docs",    "required_args": {"method": "search"}},
    {"tool_name": "rbac",    "required_args": {}}
  ]
}
```

---

## Makefile Targets

Convenience targets that wrap CLI commands. Use `make help` to list all.

### Setup

| Target | Description |
|--------|-------------|
| `make install` | Create `.venv` and install all dependencies (including dev + optional extras) |
| `make install-core` | Install core dependencies only (no dev/openai/anthropic) |

### Langfuse (local observability)

Docker Compose config lives at `docker/langfuse/docker-compose.yml` — no external cloning needed.

| Target | Description |
|--------|-------------|
| `make langfuse-up` | Start Langfuse + Postgres (UI at `http://localhost:3000`) |
| `make langfuse-down` | Stop Langfuse (data preserved in Docker volume) |
| `make langfuse-logs` | Stream Langfuse container logs |
| `make langfuse-reset` | Stop Langfuse and delete all data (volume removed) |

### Benchmark

| Target | Description |
|--------|-------------|
| `make validate` | Validate all benchmark data (equivalent to `aobench validate benchmark`) |
| `make run` | Run a single task (overridable: `TASK=`, `ENV=`, `ADAPTER=`) |
| `make run-alpha0` | Run Alpha-0 slice: JOB_USR_001 + env_01 + direct_qa |
| `make run-openai` | Run a task with OpenAI adapter (overridable: `TASK=`, `ENV=`, `MODEL=`) |
| `make run-all` | Run all tasks (one run dir, one trace per task; ADAPTER= overridable) |
| `make run-all-openai` | Run all tasks with OpenAI (MODEL= overridable) |
| `make run-anthropic` | Run a task with Anthropic adapter (TASK=, ENV=, MODEL= overridable) |
| `make run-all-anthropic` | Run all tasks with Anthropic (MODEL= overridable, default `claude-sonnet-4-6`) |
| `make run-mcp` | Run a task via MCP server (TASK=, ENV=, MCP_SERVER= overridable) |
| `make run-langfuse` | Run a task and export traces + scores to Langfuse (TASK=, ENV=, ADAPTER= overridable) |
| `make run-all-langfuse` | Run all tasks and export traces + scores to Langfuse (ADAPTER= overridable) |
| `make report` | Generate JSON + HTML report for the latest run (RUN_DIR= overridable) |
| `make compare` | Diff last two runs (RUN_A= baseline, RUN_B= comparison) |
| `make robustness` | Run a task N times and report variance (TASK=, ENV=, ADAPTER=, N= overridable) |
| `make robustness-all` | Run ALL tasks N times each and report suite-level pass^k (ADAPTER=, N=, SPLIT= overridable) |
| `make clear` | Compute CLEAR scorecard for latest run (RUN_DIR=, CLEAR_OUTPUT=, ROBUSTNESS_JSON= overridable) |
| `make generate-tool-docs` | Write `hpc_tools_guide.md` into each environment's `docs/` dir (from `hpc_tool_catalog.yaml`; role auto-detected from `metadata.yaml`) |
| `make generate-tool-docs-role` | Same, but force a specific role (`TOOL_DOCS_ROLE=sysadmin`) |
| `make generate-bundles` | Generate canonical snapshot bundles `env_06–env_23` under `benchmark/environments/` |
| `make validate-bundles` | Validate all snapshot bundles against canonical schemas (exit 0 = all OK) |
| `make validate-snapshots` | Run F1–F7 fidelity validators on all `env_*/` bundles; write `data/fidelity/` |
| `make validate-tasks` | Run T1–T10 task validity checks on the task corpus (outputs JSON report to stdout) |
| `make validate-hpc-tasks` | Validate HPC task set v1 (`benchmark/tasks/task_set_v1.json`) — prints per-data-type counts |
| `make oracle-check` | Check that each task's gold answer is derivable from snapshot data |
| `make independence-check` | Detect near-duplicate tasks by cosine similarity of feature vectors |
| `make coverage-matrix` | Print task coverage matrix (role × category) |
| `make scoring-dims` | Print the scoring dimensions reference (all terms defined) |
| `make upgrade-rbac-yaml` | Upgrade all `rbac_policy.yaml` files v1.0 → v1.1 (adds `allowed_tools`, `partition_access`, `access_tiers`, all 5 roles) |
| `make create-rbac-policy-docs` | Create `docs/rbac_policy.md` in all environment bundles (canonical τ-bench-style policy document) |

**Example with overrides:**

```bash
make run TASK=JOB_USR_002 ENV=env_02
make run-openai MODEL=gpt-4o
make run-anthropic MODEL=claude-sonnet-4-6
make run-all
make run-all-openai MODEL=gpt-4o
make run-all-anthropic MODEL=claude-sonnet-4-6
```

### Quality

| Target | Description |
|--------|-------------|
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-cov` | Run tests with coverage report |
| `make lint` | Check code style with ruff |
| `make format` | Auto-format code with ruff |
| `make typecheck` | Run mypy type checker |
| `make check` | Run lint + typecheck + tests (full CI check) |

### Leaderboard

| Target / Command | Description |
|------------------|-------------|
| `make leaderboard LEADERBOARD_RESULTS=<dir>` | Build CLEAR leaderboard from per-model result folders |
| `make leaderboard-serve` | Start the leaderboard HTTP API (requires `fastapi` + `uvicorn`: `uv add fastapi uvicorn`) |
| `aobench leaderboard build RESULTS_DIR` | Build and export leaderboard tables (JSON + CSV + heatmap) |

**`aobench leaderboard build` options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir PATH` | `RESULTS_DIR/leaderboard/` | Output directory |
| `--reliability-k INT` | `8` | k for pass^k reliability column |
| `--pass-threshold FLOAT` | `0.5` | Minimum score counted as a pass |
| `--no-heatmap` | — | Skip writing `heatmap.csv` |
| `--format [json\|csv\|all]` | `all` | Which output files to write |
| `--append PATH` | — | Merge with an existing leaderboard JSON |

**Output files:**

| File | Description |
|------|-------------|
| `leaderboard.json` | Full CLEAR report with all model scores |
| `leaderboard.csv` | Flat CSV with per-model CLEAR scores and category pass rates |
| `heatmap.csv` | Per-task × model reliability table with pass@k columns |

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `LEADERBOARD_ADMIN_PASSWORD` | `changeme` | Password for `POST /admin/rebuild` (HTTP Basic, username `admin`) |

**Endpoints (when FastAPI is installed):**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/leaderboard` | All CLEAR rows sorted by `clear_score` descending |
| `POST` | `/submit` | Submit a new model with result rows |
| `GET` | `/model/{model_id}` | ModelEntry + CLEARRow for one model |
| `GET` | `/verify/{model_id}` | VerificationResult for one model |
| `GET` | `/health` | Health check (`{"status": "ok"}`) |
| `POST` | `/admin/rebuild` | Recompute all CLEAR scores (admin auth required) |

**Install optional deps and serve:**

```bash
uv add fastapi uvicorn
make leaderboard-serve
# API running at http://127.0.0.1:8000
```

### Housekeeping

| Target | Description |
|--------|-------------|
| `make clean` | Remove build artifacts, caches, and coverage reports |
| `make clean-runs` | Remove all benchmark run artifacts from `data/runs/` |
| `make build` | Build distributable package |
| `make help` | Show all Makefile targets and descriptions |
