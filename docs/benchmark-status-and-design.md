# ExaBench Benchmark — Current Status & Design Notes

**Status:** Draft · **Owner:** Mohsen

---

## 1. Situation: Where the Benchmark Stands

ExaBench has an **alpha benchmark** — enough structure to run tasks and produce traces, but not enough to support full evaluation or a published benchmark suite.

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| **Task specs (JSON)** | ✅ Usable | 10 specs in `benchmark/tasks/specs/*.json` |
| **Environments env_01, env_02** | ⚠️ Scaffolded | Bundles exist; validation not done |
| **Tool registry** | ✅ Usable | Role → tools defined |
| **Run pipeline** | ✅ Working | Tasks run, traces written, basic scoring |

### What Blocks Full Benchmark Use

1. **Missing task specs** — MON_SYS_003, ENERGY_FAC_001, ENERGY_FAC_002, ENERGY_FAC_003 have no JSON specs.
2. **Missing environments** — env_03 (thermal/power) and env_04 (rack energy) are referenced by tasks but do not exist.
3. **Gold evidence not anchored** — `gold_evidence_refs` point at paths (e.g. `stderr/job_001.err`, `prometheus/node_metrics_001.parquet`) that are often not present in the environment bundles.
4. **Validation and scoring blocked** — All tasks: `scoring_readiness: blocked`, `gold_evidence_status: missing`; environments: `validation_status: not_checked`.
5. **Placeholder artifacts** — `incidents/incident_metadata.json` is a placeholder.
6. **Path inconsistencies** — `bundle_root` in metadata (`data/environments/env_01`) vs actual path (`benchmark/environments/env_01`).

---

## 2. The Problem in One Sentence

> **The benchmark has enough structure to run a subset of tasks end-to-end, but lacks complete environments, aligned gold evidence, and validation — so it cannot yet support meaningful evaluation or publication.**

---

## 3. Should Tasks Live Inside the Benchmark Directory?

**Current layout:** Tasks are *already* inside the benchmark directory:

```
benchmark/
├── tasks/           # Task specs
│   └── specs/*.json
├── environments/    # Environment bundles
│   ├── env_01/
│   └── env_02/
├── configs/         # Tool registry, scoring profiles
└── qa/              # Query corpus, RAG, schemas
```

### Option A: Tasks Inside Benchmark (Current)

```
benchmark/
├── tasks/
├── environments/
├── configs/
└── qa/
```

**Pros:**
- **Single benchmark package** — One directory contains everything needed to run the benchmark.
- **Simple discovery** — `exabench run task -t JOB_USR_001` and loaders can assume a fixed layout.
- **Version together** — Tasks and environments evolve in one repo; easier to keep refs consistent.
- **Conventional** — Many benchmarks (GLUE, SuperGLUE, MMLU) keep tasks and data together.

**Cons:**
- Tasks that span multiple environments can create cross-dependencies.
- Very large benchmark suites might benefit from splitting into sub-packages.

---

### Option B: Tasks Separate from Benchmark (e.g. `tasks/` at repo root)

```
ExaBench/
├── tasks/           # Task specs only
├── benchmark/       # Environments, configs, qa
│   ├── environments/
│   └── configs/
└── src/
```

**Pros:**
- Clear separation: *what to ask* (tasks) vs *where to run* (environments).
- Tasks could be shared across different benchmark variants.

**Cons:**
- **Coupling anyway** — Tasks reference `environment_id` and `gold_evidence_refs` that live in environments. They are coupled by design.
- **Two roots to maintain** — Loaders and tooling must know both `tasks/` and `benchmark/`.
- **No strong benefit at this scale** — For ~30 tasks, extra complexity rarely pays off.

---

### Option C: Tasks Per Environment (Distributed)

```
benchmark/
├── environments/
│   ├── env_01/
│   │   ├── tasks/           # Tasks that use env_01
│   │   └── slurm/, telemetry/, ...
│   ├── env_02/
│   │   ├── tasks/
│   │   └── ...
│   └── env_03/
│       └── ...
```

**Pros:**
- Strong locality: each env ships with its tasks.
- Easy to add/remove envs without touching a central registry.

**Cons:**
- **Duplicate registry** — No single place to list all tasks or filter by category/role.
- **Cross-env queries harder** — “Compare env_01 and env_02” or “all JOB tasks” require scanning all envs.
- **Mismatch with current model** — ExaBench architecture (03) treats tasks and environments as separate entities linked by `environment_id`. Colocating them would blur that boundary.

---

## 4. Recommendation

**Keep tasks inside the benchmark directory** (Option A), as today.

1. **Tasks and environments are tightly coupled** — `environment_id` and `gold_evidence_refs` tie tasks to specific bundles. Keeping them in one `benchmark/` tree reflects that.
2. **Scale is small** — ~30 tasks, ~5 envs; a single `benchmark/` package is manageable.
3. **Discovery is simpler** — One canonical `benchmark/` path for tools, loaders, and documentation.
4. **Aligned with architecture** — The framework already models Task and Environment as separate entities; centralizing tasks in `benchmark/tasks/` keeps that model without adding layout complexity.

If the benchmark grows (e.g. 100+ tasks, multiple benchmark “editions”), consider:
- Subdirs like `benchmark/tasks/job/`, `benchmark/tasks/energy/`
- Or separate packages (e.g. `exabench-benchmark-core`, `exabench-benchmark-energy`) with clear versioning.

---

## 5. Next Steps to Unblock the Benchmark

| Priority | Action | Status |
|----------|--------|--------|
| 1 | Fix `gold_evidence_refs` to match actual files in env_01 and env_02 | ✅ Done |
| 2 | Align `bundle_root` and loader paths (metadata vs filesystem) | ✅ Done |
| 3 | Replace placeholder `incident_metadata.json` or mark as intentionally minimal | ✅ Done |
| 4 | Add 4 missing task specs (MON_SYS_003, ENERGY_FAC_001–003) | ✅ Done |
| 5 | Create env_03 and env_04 for ENERGY and rack-thermal tasks | ✅ Done |
| 6 | Run validation and set `scoring_readiness`, `validation_status` where applicable | ✅ Done |
