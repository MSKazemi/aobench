---
title: "Benchmark for AI agents that operate HPC systems"
description: "Open-source benchmark for AI agents operating HPC systems: 89 tasks, 29 deterministic snapshots, RBAC-enforced, trace-scored. No cluster needed."
keywords:
  - HPC agent benchmark
  - AI agent evaluation
  - LLM benchmark HPC
  - SLURM agent
  - RBAC agent evaluation
  - AIOps benchmark
---

<div class="hero" markdown>

<img class="hero-logo" src="assets/logo.svg" alt="AOBench logo">

<p class="hero-label">Open Source · HPC Benchmarking · AI Evaluation</p>

# AOBench

<p class="hero-sub">
The open-source benchmark for AI agents that operate High-Performance Computing systems —
role-aware, permission-enforced, tool-using, trace-scored, and reproducible on a laptop.
</p>

<div class="badge-row" markdown>
[![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-4CAF50)](https://github.com/MSKazemi/aobench/blob/main/LICENSE)
[![Version](https://img.shields.io/badge/version-0.4.1-1a237e)](https://github.com/MSKazemi/aobench/releases)
[![Tasks](https://img.shields.io/badge/tasks-89-FF6F00)](reference/task-catalog.md)
[![Environments](https://img.shields.io/badge/environments-29-0288D1)](reference/environment-catalog.md)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21854862.svg)](https://doi.org/10.5281/zenodo.21854862)
</div>

<div class="btn-row" markdown>
[Quickstart — 5 minutes](getting-started/quickstart.md){ .btn .btn-primary }
[View on GitHub](https://github.com/MSKazemi/aobench){ .btn .btn-secondary }
</div>

</div>

<ul class="stat-strip">
  <li><span class="stat-value">89</span><span class="stat-label">Tasks</span></li>
  <li><span class="stat-value">29</span><span class="stat-label">Environments</span></li>
  <li><span class="stat-value">7</span><span class="stat-label">Dimensions</span></li>
  <li><span class="stat-value">5</span><span class="stat-label">Roles</span></li>
</ul>

---

## What AOBench is

- **AOBench (Agent Operations Benchmark) is an open-source Python benchmark framework for
  evaluating AI agents that operate High-Performance Computing (HPC) systems.**
- **AOBench helps researchers and engineers measure** whether an agent completes HPC
  operational tasks — job scheduling, telemetry interpretation, energy reasoning, policy
  enforcement — with the right tools, roles, and permissions.
- **Use AOBench when you need** reproducible, role-aware, permission-enforced evaluation of
  HPC agents against deterministic environment snapshots instead of live clusters.
- **AOBench differs from general-purpose LLM-agent benchmarks** because it is domain-specific
  to HPC operations, enforces role-based access control, and scores the full execution trace
  rather than only the final answer.
- **AOBench is not intended for** measuring general-purpose reasoning, software-engineering,
  or web-browsing agents, and it does not execute against real production clusters.

Six of the 29 environments and eight of the 89 tasks are built from **real operational data**
from CINECA's 980-node Marconi100 Tier-0 supercomputer (the public
[M100 ExaData release](guides/m100_environments.md)) — not synthesised.

---

## Five benchmark principles

| Principle | Meaning |
|-----------|---------|
| **Role-aware** | The same question yields different answers and tool access depending on the requester role. |
| **Tool-using** | Agents are evaluated as systems that call HPC-native tools (SLURM, telemetry, docs, RBAC, facility). |
| **Permission-aware** | Success requires respecting RBAC and refusing out-of-scope requests. Permission violations hard-fail the task. |
| **Trace-based** | Evaluation considers the full execution trace — tool selection, arguments, sequence, and grounding — not just the final answer. |
| **Reproducible** | Runs target deterministic snapshot bundles, never live infrastructure. |

---

## Quick start

No API key and no cluster access are needed for the first run.

```bash
git clone https://github.com/MSKazemi/aobench.git && cd aobench && make install

aobench quickstart            # one command, no arguments, no API key
```

`aobench quickstart` locates the benchmark corpus, picks a representative task, runs it,
and explains every number it prints. To drive it yourself:

```bash
aobench doctor                # is the install healthy?
aobench list tasks --qcat JOB # browse the corpus
aobench run task --task JOB_USR_001 --env env_01 --adapter direct_qa
```

Expected output of the run command:

```text
Running task=JOB_USR_001  env=env_01  adapter=direct_qa

Result: aggregate_score=0.3340  hard_fail=False
  outcome=0.24  tool_use=0.0  governance=1.0  efficiency=1.0

Run ID: run_20260810_132408_8a2b57c7
```

`direct_qa` is the deliberately tool-free reference baseline — `tool_use=0.0` is the
point of it, and `0.334` is the floor a real agent should beat. See the
[quickstart](getting-started/quickstart.md) for the full walkthrough and the
[evaluate-your-own-agent guide](guides/evaluating-your-own-agent.md) to plug in your
system.

---

## Where to go next

<div class="grid cards" markdown>

-   :material-rocket-launch: **Get started**

    ---

    Install, run your first task, and read a scorecard in five minutes.

    [:octicons-arrow-right-24: Quickstart](getting-started/quickstart.md)

-   :material-book-open-variant: **Framework**

    ---

    Benchmark methodology, evaluation protocol, HPC environments, and scoring design.

    [:octicons-arrow-right-24: Read the framework docs](framework/overview.md)

-   :material-flask: **For researchers**

    ---

    Datasheet, benchmark card, reproducibility checklist, related work, and how to cite.

    [:octicons-arrow-right-24: Research surfaces](about/datasheet.md)

-   :material-account-group: **Contribute**

    ---

    Good first issues, how to add a task, an environment, an adapter, or a scorer.

    [:octicons-arrow-right-24: How to contribute](about/contributing.md)

</div>

---

## Frequently asked

**Do I need an HPC cluster to run AOBench?** No. Every task runs against a frozen snapshot
bundle with mock tools, on a laptop.

**Which models can I evaluate?** Anything reachable through the `openai`, `anthropic`, or
`mcp` adapters, plus the tool-free `direct_qa` reference baseline.

**Is it just another LLM leaderboard?** No — AOBench scores the whole trace across six
dimensions and hard-fails RBAC violations, so an agent that produces the right answer by
overstepping its role scores zero.

More in the [FAQ](about/faq.md) and the
[comparison with other agent benchmarks](about/comparison.md).
