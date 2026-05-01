# ExaBench Framework Documentation

**ExaBench** is a benchmark framework for evaluating AI agent systems in
High-Performance Computing (HPC) environments. It uses role-aware tasks,
deterministic HPC state snapshots, and trace-based scoring across six
dimensions.

This index is the entry point to the framework documentation. Every page
here describes the system **as implemented**; the documentation cleanup of
2026-05-02 removed early-draft material that no longer matched the code, and
moved unimplemented ideas to `.claude/plans/2026-05-02-future-work.md`.

---

## Document map

| Document | Purpose |
|----------|---------|
| [Overview](overview.md) | Five principles, v0.1 implemented scope, long-term goal |
| [Background](background.md) | Motivation, the gap, related work |
| [Architecture](architecture.md) | Conceptual benchmark architecture: layers, entities, workflow |
| [Implementation](implementation.md) | Developer guide: how to extend adapters, tools, scorers, tasks |
| [Environments](environments.md) | Snapshot bundle format and core design |
| [Evaluation](evaluation.md) | Evaluation protocol, twelve scorers, hard-fail rules, trace and result schemas |
| [Taxonomy](taxonomy.md) | Roles, QCATs, knowledge sources, RBAC tiers, task metadata schema |
| [System Architecture](system-architecture.md) | **Authoritative current-state reference** — three-repo ecosystem, component map, end-to-end data flow, scoring pipeline, CLEAR scorecard |
| [Scoring Dimensions](scoring-dimensions.md) | Per-scorer formulas and weight profiles |

When in doubt about scope numbers or component names,
**[`system-architecture.md`](system-architecture.md) is ground truth**. The
other framework pages stay aligned with it as a matter of policy; if you
spot a divergence, the divergence is a bug.

---

## Outside this directory

| Document | Purpose |
|----------|---------|
| [`docs/reference/commands.md`](../reference/commands.md) | Full CLI reference (every flag of every sub-command) |
| [`docs/reference/environments-overview.md`](../reference/environments-overview.md) | Inventory of all 20 environment bundles |
| [`docs/guides/adapters-and-tools.md`](../guides/adapters-and-tools.md) | Plain-English adapter and tool guide |
| [`docs/reference/architecture-flowchart.md`](../reference/architecture-flowchart.md) | Mermaid diagrams |
| [`docs/guides/langfuse-integration.md`](../guides/langfuse-integration.md) | Observability backend |
| [`docs/guides/paper-reproduction.md`](../guides/paper-reproduction.md) | Reproducing v0.1 paper tables |
| [`.claude/plans/2026-05-02-roadmap.md`](../../.claude/plans/2026-05-02-roadmap.md) | Open backlog and next milestones |
| [`README.md`](../../README.md) | Repository entry point and quick start |
| [`CHANGELOG.md`](../../CHANGELOG.md) | Release notes |
| [`CONTRIBUTING.md`](../../CONTRIBUTING.md) | Contribution guide |
| [`SECURITY.md`](../../SECURITY.md) | Vulnerability reporting and threat model |

---

## Quick links

- Run the benchmark: [`COMMANDS.md`](../reference/commands.md)
- All component responsibilities: [system-architecture §2](system-architecture.md)
- End-to-end data flow: [system-architecture §4](system-architecture.md)
- Scoring pipeline: [system-architecture §5](system-architecture.md)
- CLEAR scorecard formula: [system-architecture §6](system-architecture.md)
- Implemented dataset scope: [overview §3](overview.md)
- Environment inventory: [`environments-overview.md`](../reference/environments-overview.md)
