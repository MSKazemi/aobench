# ExaBench Framework Documentation

## Overview

**ExaBench** is a benchmark framework for evaluating AI agents in High-Performance Computing (HPC) environments. It uses role-aware tasks, deterministic HPC state snapshots, and trace-based scoring across six dimensions.

---

## Document Map

| # | Document | Purpose | Status |
|---|----------|---------|--------|
| 09 | [**System Architecture**](09-system-architecture.md) | **Authoritative current-state reference** — 3-repo ecosystem, component map, data flow, scoring pipeline, CLEAR scorecard | Current |
| 01 | [Overview](01-overview.md) | Principles, v0.1 scope declaration | Partially stale (scope numbers) |
| 02 | [Background](02-background.md) | Motivation, related work | Current |
| 03 | [Architecture](03-architecture.md) | Benchmark design: layers, entities, workflow | Partially stale |
| 04 | [Implementation](04-implementation.md) | Software architecture, CLI, adapters, tools | Partially stale (scorer section) |
| 05 | [Environments](05-environments.md) | Environment snapshot format and loading | Current |
| 06 | [Evaluation](06-evaluation.md) | Evaluation protocol, metrics, trace schema | Partially stale (missing CheckpointScorer, WorfEvalScorer) |
| 07 | [Taxonomy](07-taxonomy.md) | Roles, categories, access control, query schema | Current |
| — | [COMMANDS.md](../COMMANDS.md) | Full CLI command reference | Current |
| — | [Scoring Dimensions](scoring-dimensions.md) | Scorer detail reference | Partially stale |

> **When in conflict between documents, `09-system-architecture.md` is the ground truth.** Earlier docs describe the originally planned v0.1 scope, not the implemented system.

---

## Quick Links

- **Running the benchmark**: `docs/COMMANDS.md`
- **All component responsibilities**: `09-system-architecture.md §2`
- **End-to-end data flow**: `09-system-architecture.md §4`
- **Scoring pipeline**: `09-system-architecture.md §5`
- **CLEAR scorecard formula**: `09-system-architecture.md §6`
- **Dataset scope (actual vs planned)**: `09-system-architecture.md §3`
- **What's stale in older docs**: `09-system-architecture.md §10`
