# ExaBench Framework Documentation

**ExaBench** is a benchmark framework for evaluating AI agent systems in
High-Performance Computing (HPC) environments. It uses role-aware tasks,
deterministic HPC state snapshots, and trace-based scoring across six
dimensions.

This index is the entry point to the framework documentation.

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
| [System Architecture](../reference/system-architecture.md) | **Authoritative current-state reference** — component map, end-to-end data flow, scoring pipeline, CLEAR scorecard, architecture diagrams |
| [Scoring Dimensions](scoring-dimensions.md) | Per-scorer formulas and weight profiles |

For a complete component map, end-to-end data flow, and scoring pipeline details, see [System Architecture](../reference/system-architecture.md).

---

## Outside this directory

| Document | Purpose |
|----------|---------|
| [`docs/reference/commands.md`](../reference/commands.md) | Full CLI reference (every flag of every sub-command) |
| [`docs/reference/environments-overview.md`](../reference/environments-overview.md) | Inventory of all 23 environment bundles |
| [`docs/guides/adapters-and-tools.md`](../guides/adapters-and-tools.md) | Plain-English adapter and tool guide |
| [`docs/reference/system-architecture.md`](../reference/system-architecture.md) | System architecture + Mermaid diagrams |
| [`docs/guides/langfuse-integration.md`](../guides/langfuse-integration.md) | Observability backend |
| [`CONTRIBUTING.md`](../about/contributing.md) | How to contribute tasks, adapters, scorers |
| [GitHub README](https://github.com/MSKazemi/ExaBench#readme) | Repository entry point and quick start |
| [`CHANGELOG.md`](../about/changelog.md) | Release notes |
| [`CONTRIBUTING.md`](../about/contributing.md) | Contribution guide |
| [`SECURITY.md`](../about/security.md) | Vulnerability reporting and threat model |

---

## Quick links

- Run the benchmark: [`COMMANDS.md`](../reference/commands.md)
- All component responsibilities: [system-architecture §2](../reference/system-architecture.md)
- End-to-end data flow: [system-architecture §4](../reference/system-architecture.md)
- Scoring pipeline: [system-architecture §5](../reference/system-architecture.md)
- CLEAR scorecard formula: [system-architecture §6](../reference/system-architecture.md)
- Implemented dataset scope: [overview §3](overview.md)
- Environment inventory: [`environments-overview.md`](../reference/environments-overview.md)
