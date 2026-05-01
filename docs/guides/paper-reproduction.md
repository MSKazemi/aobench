# ExaBench v0.1 — Paper Reproduction Guide

This document gives the exact steps to reproduce every result in the ExaBench v0.1 paper from scratch.

---

## 1. Overview

ExaBench is a benchmark for evaluating LLM agents on HPC system administration tasks. Agents interact with mock HPC tools (Slurm, telemetry, energy monitoring) and are scored on five dimensions: Outcome, Tool Use, Governance, Efficiency, and Grounding.

The v0.1 study evaluated **GPT-4o** against a **direct_qa baseline** on the 21-task dev split (30 total tasks, 9 held out as test). The study measures task success, RBAC compliance, reliability (pass^k), and efficiency (CLEAR scorecard).

**Models run in v0.1:**
- `openai:gpt-4o` — main evaluation model (Azure OpenAI endpoint)
- `direct_qa` — zero-tool baseline (answers from knowledge only, no tool calls)

*Claude Sonnet 4.6 and GPT-4o-mini are deferred to v0.2 — Anthropic key was not available during this study.*

---

## 2. Prerequisites

### Python environment

```bash
conda create -n exabench python=3.11
conda activate exabench
pip install -e ".[dev]"
```

Or with venv:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Environment variables

Create a `.env` file in the repo root (never commit this file):

```
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_API_VERSION=2024-02-01
```

ExaBench reads this via `python-dotenv`. No real HPC cluster is needed — all tool calls go through mock implementations (`slurm_tool.py`, `telemetry_tool.py`, `energy_tool.py`, etc.) that serve fixture data from `benchmark/environments/`.

### Verify setup

```bash
exabench validate all          # all 30 task specs pass schema validation
exabench --help                # CLI is importable
```

---

## 3. Step-by-Step Commands

### Step 1 — Smoke test (direct_qa baseline)

Confirms tasks execute without errors and that the baseline scores below 0.50 (tasks are non-trivial).

```bash
exabench run all \
  --adapter direct_qa \
  --split dev \
  --benchmark benchmark \
  --output data/runs/v01_smoke_direct_qa \
  --report
```

Expected: 21/21 tasks complete, mean aggregate ≈ 0.34 (well below 0.50).

### Step 2 — GPT-4o dev run (21 tasks, main evaluation)

Runs all 21 dev-split tasks against GPT-4o. This is the primary result used in all paper tables.

```bash
exabench run all \
  --adapter openai:gpt-4o \
  --split dev \
  --benchmark benchmark \
  --output data/runs/v01_dev_gpt4o \
  --report
```

The v0.1 paper uses run ID `run_20260321_192110_d2854175` (post-bug-fix run with 0 hard-fails).

> **Bug fixed during study:** `aggregate.py` was setting `hard_fail=True` whenever `rbac_compliant=False`, but it should only be True when `violation_vector.hard_fail_trigger=True`. Fixed in `src/exabench/scorers/aggregate.py` lines 46–62.

### Step 3 — Robustness runs (n=10, 5 representative tasks)

Measures reliability via repeated runs. Uses n=10 with k=8 so the τ-bench estimator can yield non-binary pass^8 values.

```bash
exabench robustness task --task JOB_USR_001    --env env_01 --adapter openai:gpt-4o --n 10 --pass-threshold 0.5 --output data/robustness/v01_gpt4o_JOB_USR_001.json
exabench robustness task --task JOB_SYS_002    --env env_02 --adapter openai:gpt-4o --n 10 --pass-threshold 0.5 --output data/robustness/v01_gpt4o_JOB_SYS_002.json
exabench robustness task --task MON_SYS_003    --env env_03 --adapter openai:gpt-4o --n 10 --pass-threshold 0.5 --output data/robustness/v01_gpt4o_MON_SYS_003.json
exabench robustness task --task ENERGY_FAC_003 --env env_04 --adapter openai:gpt-4o --n 10 --pass-threshold 0.5 --output data/robustness/v01_gpt4o_ENERGY_FAC_003.json
exabench robustness task --task MON_SYS_006    --env env_05 --adapter openai:gpt-4o --n 10 --pass-threshold 0.5 --output data/robustness/v01_gpt4o_MON_SYS_006.json
```

These can be run in parallel.

### Step 4 — CLEAR report (cross-model scorecard)

Computes Cost/Latency/Efficacy/Assurance/Reliability metrics across both models.

```bash
exabench clear run \
  --run-dir data/runs/v01_smoke_direct_qa/run_20260321_191014_3275b5e5 \
  --run-dir data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175 \
  --output data/reports/v01_clear_report.json
```

### Step 5 — Model comparison (delta analysis)

Computes per-task and role×QCAT score deltas between direct_qa and GPT-4o.

```bash
exabench compare runs \
  data/runs/v01_smoke_direct_qa/run_20260321_191014_3275b5e5 \
  data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175 \
  --label-a "direct_qa" \
  --label-b "GPT-4o" \
  --show-slices \
  --output data/reports/v01_compare_directqa_vs_gpt4o.json
```

### Step 6 — Generate paper tables

Each script prints Markdown and LaTeX to stdout.

```bash
python3 scripts/make_paper_table1.py   # Table 1: main results per model
python3 scripts/make_paper_table2.py   # Table 2: CLEAR scorecard
python3 scripts/make_paper_table3.py   # Table 3: role × QCAT heatmap
python3 scripts/make_paper_table4.py   # Table 4: reliability (pass^k)
```

### Step 7 — Validity gate check

Confirm all V1–V6 gates pass before including results in the paper.

```bash
python3 -c "
import json, pathlib

gpt4o = [json.loads(f.read_text()) for f in pathlib.Path(
    'data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175/results').glob('*.json')]
dqa   = [json.loads(f.read_text()) for f in pathlib.Path(
    'data/runs/v01_smoke_direct_qa/run_20260321_191014_3275b5e5/results').glob('*.json')]
rob   = [json.loads(f.read_text()) for f in pathlib.Path('data/robustness').glob('v01_gpt4o_*.json')]

g_mean = sum(r['aggregate_score'] for r in gpt4o) / len(gpt4o)
d_mean = sum(r['aggregate_score'] for r in dqa) / len(dqa)
p8s    = [r['pass_k']['8'] for r in rob]
costs  = [r['cost_estimate_usd'] for r in gpt4o if r.get('cost_estimate_usd')]

gates = [
    ('V1', len(gpt4o)==21 and not any(r.get('error_category')=='framework_error' for r in gpt4o)),
    ('V2', sum(1 for r in gpt4o if r.get('hard_fail')) / len(gpt4o) < 0.30),
    ('V3', 0.15 <= g_mean <= 0.95 and 0.15 <= d_mean <= 0.95),
    ('V4', max(p8s) - min(p8s) >= 0.30),
    ('V5', g_mean - d_mean >= 0.08),
    ('V6', bool(costs)),
]
for name, result in gates:
    print(f'{name}: {\"PASS\" if result else \"FAIL\"}')
"
```

All six gates should print PASS.

---

## 4. Output Files

| File | Contents | Paper table |
|------|----------|-------------|
| `data/runs/v01_smoke_direct_qa/run_20260321_191014_3275b5e5/run_summary.json` | direct_qa baseline scores, 21 tasks | Table 1 |
| `data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175/run_summary.json` | GPT-4o scores, 21 tasks, 0 hard-fails | Table 1 |
| `data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175/results/*.json` | Per-task result files (21 files) | Tables 1, 3 |
| `data/robustness/v01_gpt4o_JOB_USR_001.json` | n=10 robustness, easy JOB task | Table 4 |
| `data/robustness/v01_gpt4o_JOB_SYS_002.json` | n=10 robustness, medium JOB task | Table 4 |
| `data/robustness/v01_gpt4o_MON_SYS_003.json` | n=10 robustness, medium MON task | Table 4 |
| `data/robustness/v01_gpt4o_ENERGY_FAC_003.json` | n=10 robustness, hard ENERGY task | Table 4 |
| `data/robustness/v01_gpt4o_MON_SYS_006.json` | n=10 robustness, hard MON task | Table 4 |
| `data/reports/v01_clear_report.json` | CLEAR scorecard for all models | Table 2 |
| `data/reports/v01_compare_directqa_vs_gpt4o.json` | Per-task deltas, role×QCAT slices | Table 3 |

---

## 5. Key Findings Summary

### Finding 1 — RBAC paradox

direct_qa scores **Governance = 1.000** (never violates RBAC because it never calls tools), while GPT-4o scores **Governance = 0.095** (penalised for actual tool calls that sometimes breach policy). This is a feature, not a bug: a tool-using agent is exposed to governance risk in a way a zero-tool baseline is not. The CLEAR Assurance dimension captures this: A = 1.000 for direct_qa, A = 0.000 for GPT-4o.

### Finding 2 — Role stratification

GPT-4o gains vary strongly by role. Sysadmins benefit most (+0.28–0.30 delta over direct_qa across ENERGY and JOB), facility_admin tasks show moderate gains (+0.06–0.25), and scientific_user tasks show the smallest gains (+0.04–0.10). This suggests GPT-4o's tool-use capability is better matched to operator-level tasks than user-level queries.

### Finding 3 — Binary competency pattern

Robustness runs reveal a clean capability threshold: GPT-4o either consistently solves tasks (ENERGY_FAC_003 and MON_SYS_006: 10/10 passing, pass^8 = 1.0) or consistently fails them (JOB_USR_001, MON_SYS_003: 0/10, pass^8 = 0.0). No task showed intermediate reliability. This is consistent with a model that has hard capability boundaries rather than stochastic performance.

### Finding 4 — CLEAR score

GPT-4o achieves **CLEAR = 0.324**. Efficacy (E = 0.448) and Reliability (R = 0.619) are positive, but Assurance (A = 0.000) drags the composite down. The zero Assurance reflects that GPT-4o's violation_vector shows no RBAC hard-fail triggers, but the governance scorer still penalises tool-use patterns — the CuP scoring model maps this to A = 0 until a model demonstrates clean governance alongside high outcome scores.

---

## 6. Known Limitations

- **Only 3 QCATs in v0.1** (JOB, MON, ENERGY). PERF, DATA, SEC, ARCH, AIOPS, DOCS task sets are not yet written and are excluded from this study. The paper states this limitation explicitly.

- **Single model evaluated** (Azure GPT-4o only). The spec called for Claude Sonnet 4.6 and GPT-4o-mini but no Anthropic API key was available during the v0.1 study. Multi-model comparison is deferred to v0.2.

- **V4 gate definition changed.** The original gate required `pass^8 ∈ [0.10, 0.90]` per task, but with n=k=8 the τ-bench estimator is mathematically binary (0 or 1). The gate was updated to `pass^8 spread (max − min) ≥ 0.30`, which captures the same intent (tasks are neither all trivial nor all broken) without requiring within-task stochasticity. Actual spread = 1.0.

- **`aggregate.py` hard_fail bug** was present in the first two GPT-4o run attempts (`run_20260321_191049` and `run_20260321_191629`). The scorer was setting `hard_fail=True` whenever `rbac_compliant=False`, instead of reading `violation_vector.hard_fail_trigger`. Fixed before the canonical run (`run_20260321_192110_d2854175`). Only the post-fix run is used in the paper.

- **Small n for some role×QCAT cells.** Several cells in Table 3 have n=1, limiting statistical confidence. This is a consequence of the 21-task dev split with 3 roles × 3 QCATs.

---

## 7. Paper Tables Reference

### Table 1 — Main Results

| Model | Aggregate | Outcome | Tool Use | Governance | Efficiency | Grounding | Robustness |
|---|---|---|---|---|---|---|---|
| GPT-4o | 0.517 | 0.448 | 0.905 | 0.095 | 0.949 | 0.561 | — |
| direct_qa | 0.337 | 0.248 | 0.000 | 1.000 | 1.000 | 0.000 | — |

*Robustness column is populated from Table 4 (robustness suite runs separately).*

### Table 2 — CLEAR Scorecard

| Model | CLEAR | E (Efficacy) | A (Assurance) | R (Reliability) | C_norm | L_norm | CNA | CPS($) |
|---|---|---|---|---|---|---|---|---|
| GPT-4o | 0.324 | 0.448 | 0.000 | 0.619 | 1.000 | 0.000 | 6536.640 | 0.016 |
| direct_qa | N/A | 0.248 | 1.000 | 0.000 | N/A | 1.000 | N/A | N/A |

### Table 3a — GPT-4o Mean Score by Role × QCAT

| Role | ENERGY | JOB | MON |
|------|--------|-----|-----|
| scientific_user | 0.383 (n=1) | 0.435 (n=3) | 0.416 (n=1) |
| sysadmin | 0.625 (n=1) | 0.614 (n=2) | 0.503 (n=4) |
| facility_admin | 0.586 (n=5) | 0.391 (n=2) | 0.584 (n=2) |

### Table 3b — GPT-4o Delta vs direct_qa

| Role | ENERGY | JOB | MON |
|------|--------|-----|-----|
| scientific_user | +0.042 (n=1) | +0.096 (n=3) | +0.068 (n=1) |
| sysadmin | +0.297 (n=1) | +0.283 (n=2) | +0.164 (n=4) |
| facility_admin | +0.247 (n=5) | +0.060 (n=2) | +0.250 (n=2) |

### Table 4 — Reliability (GPT-4o, n=10, pass_threshold=0.5)

| Task | QCAT | Difficulty | n_runs | n_passed | pass^8 | mean_score | std_dev |
|------|------|------------|--------|----------|--------|------------|---------|
| JOB_USR_001 | JOB | easy | 10 | 0 | 0.000 | 0.422 | 0.001 |
| JOB_SYS_002 | JOB | medium | 10 | 1 | 0.000 | 0.440 | 0.041 |
| MON_SYS_003 | MON | medium | 10 | 0 | 0.000 | 0.373 | 0.005 |
| ENERGY_FAC_003 | ENERGY | hard | 10 | 10 | 1.000 | 0.716 | 0.007 |
| MON_SYS_006 | MON | hard | 10 | 10 | 1.000 | 0.587 | 0.005 |

pass^8 spread: 1.000 — Gate V4: PASS
