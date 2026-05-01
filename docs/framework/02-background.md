# 02 — Background: Motivation & Related Work

**Owner:** Mohsen

This page summarizes why ExaBench exists and how it relates to the broader benchmark landscape.

---

## 1. Why ExaBench Is Needed

AI agents are increasingly proposed for HPC support, operations, and monitoring. There is currently **no benchmark** that evaluates such agents under HPC constraints: scheduler-aware reasoning, telemetry interpretation, role-conditioned answers, permission-sensitive behavior, and reproducible operational-state evaluation.

Existing benchmarks cover web agents, software-engineering agents, enterprise workflows, and cloud operations—but not the combination required in HPC.

---

## 2. The Gap

No existing benchmark, to our knowledge, simultaneously provides:

- **HPC-native tool environment** (schedulers, telemetry, docs, energy, facility)
- **Role-aware task variants** (same question, different answers by role)
- **Deterministic HPC state snapshots** for reproducibility
- **Permission compliance scoring** (refusal quality, redaction, RBAC)
- **Trace-based evaluation** (tool selection, arguments, grounding)
- **Energy- and facility-aware tasks** as first-class components

---

## 3. Benchmark Landscape (Condensed)

| Category | Examples | Relevance |
|----------|----------|-----------|
| General agent | AgentBench, GAIA | Broad capability; not HPC-specific |
| Environment-based | WebArena, OSWorld | Executable settings; methodologically relevant |
| Domain-specific | τ-bench, Cloud-OpsBench | Policy-aware, deterministic state; closest analogues |
| Tool-use | TRAIL, ToolBench | API selection, argument correctness |
| Trace-based | Various | Process scoring, not just outcome |

**τ-bench** (policy-aware) and **Cloud-OpsBench** (deterministic operational state) are the closest methodological analogues. Neither addresses HPC-native tools, role-aware access, or energy/facility reasoning.

---

## 4. ExaBench's Contribution

1. **New benchmark domain:** HPC agent systems
2. **Role-aware task model:** evaluation conditioned on stakeholder role
3. **Deterministic replay environment:** reproducible HPC telemetry and policy
4. **Trace-based protocol:** scoring outcomes and agent trajectories
5. **Multi-dimensional scorecard:** accuracy, tool use, grounding, compliance, robustness, efficiency

---

## 5. Positioning

> **ExaBench is a benchmark framework for evaluating AI agents in HPC environments using role-aware tasks, deterministic HPC state snapshots, and trace-based scoring.**

For the extended literature notes that informed this positioning, see
`../ExaBench-SoA/Appendix — Extended Literature Notes.md` and the 35-paper
inventory under `../ExaBench-SoA/inventory/resources.csv`.
