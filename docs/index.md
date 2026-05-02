<div class="hero" markdown>

<p class="hero-label">Open Source · HPC Benchmarking · AI Evaluation</p>

# ExaBench

<p class="hero-sub">
Benchmark framework for evaluating AI agents in High-Performance Computing (HPC) environments —
role-aware, tool-using, trace-based, and reproducible.
</p>

<div class="badge-row" markdown>
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-4CAF50)](https://github.com/MSKazemi/ExaBench/blob/main/LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-1a237e)](https://github.com/MSKazemi/ExaBench/releases)
[![Tasks](https://img.shields.io/badge/tasks-30-FF6F00)](benchmark/tasks/)
[![Environments](https://img.shields.io/badge/environments-20-0288D1)](benchmark/environments/)
</div>

<div class="btn-row" markdown>
[Get Started](framework/overview.md){ .btn .btn-primary }
[View on GitHub](https://github.com/MSKazemi/ExaBench){ .btn .btn-secondary }
</div>

</div>

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
