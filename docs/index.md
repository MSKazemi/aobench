# ExaBench

**Benchmark framework for evaluating AI agents in High-Performance Computing (HPC) environments.**

ExaBench measures how well AI agents complete HPC operational tasks — job scheduling, telemetry interpretation,
energy reasoning, policy enforcement — using the right tools, the right roles, and the right permissions.
Every task runs against a deterministic environment snapshot with mock HPC tools, so results are
reproducible, portable, and safe to publish.

---

## Five Benchmark Principles

| Principle | Meaning |
|-----------|---------|
| **Role-aware** | The same question yields different answers and tool access depending on the requester role. |
| **Tool-using** | Agents are evaluated as systems that call HPC-native tools (SLURM, telemetry, docs, RBAC, facility). |
| **Permission-aware** | Success requires respecting RBAC and refusing out-of-scope requests. Permission violations hard-fail the task. |
| **Trace-based** | Evaluation considers the full execution trace — tool selection, arguments, sequence, and grounding — not just the final answer. |
| **Reproducible** | Runs target deterministic snapshot bundles, never live infrastructure. |

---

## Quick Start

```bash
pip install "exabench[openai]"

# Validate all task specs and environment bundles
exabench validate benchmark

# Run one task end-to-end with the zero-tool baseline
exabench run task --task JOB_USR_001 --env env_01 --adapter direct_qa

# Generate a report
exabench report json --run data/runs/<run-id>
```

---

## Where to Go Next

<div class="grid cards" markdown>

-   :material-book-open-variant: **Concepts**

    ---

    Benchmark methodology, scoring dimensions, evaluation protocol, and the HPC error taxonomy.

    [:octicons-arrow-right-24: Read the framework docs](framework/overview.md)

-   :material-console: **Usage**

    ---

    CLI reference, adapter guide, Langfuse integration, and paper reproduction instructions.

    [:octicons-arrow-right-24: Browse usage guides](guides/adapters-and-tools.md)

-   :material-github: **GitHub**

    ---

    Source code, issue tracker, and contribution guide.

    [:octicons-arrow-right-24: MSKazemi/ExaBench](https://github.com/MSKazemi/ExaBench)

</div>
