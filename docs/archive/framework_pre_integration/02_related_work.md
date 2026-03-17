# 02 — Related Work / Positioning

Owner: Mohsen

# Innovation & Gap

## Why ExaBench is Needed

Despite rapid progress in LLM-agent benchmarking, the current landscape still lacks a benchmark tailored to the realities of **High-Performance Computing (HPC)**. Existing benchmarks evaluate agents for web navigation, software engineering, enterprise workflows, general tool use, or cloud operations, but they do not capture the combination of requirements that defines HPC environments.

HPC agents must operate across a heterogeneous operational stack that includes **job schedulers, telemetry systems, policy documents, energy and facility data, and role-dependent access constraints**. They must also support multiple stakeholder groups, including end users, researchers, system administrators, facility operators, and HPC architects. This combination of **tool use, infrastructure reasoning, role awareness, and operational governance** is not jointly addressed by current benchmarks.

As shown in the State-of-the-Art review, several existing benchmarks provide important methodological building blocks. Environment-based benchmarks demonstrate the value of executable and reproducible task settings; domain-specific benchmarks show the importance of policy-sensitive interaction; tool-use benchmarks provide methods for evaluating API selection and argument correctness; and trace-based benchmarks highlight the need to score not only outcomes but also the reasoning and execution process. However, none of them provides an **HPC-native evaluation framework**.

ExaBench is motivated by this gap: the absence of a benchmark that evaluates AI agents as **interactive, tool-using, permission-aware systems for HPC environments**.

---

## The Core Research Gap

No existing benchmark simultaneously provides:

- an **HPC-native tool environment** spanning schedulers, telemetry, documentation, energy data, and facility signals
- **role-aware task variants** in which the same operational question must be answered differently depending on the user’s role and permissions
- **deterministic HPC state snapshots** for reproducible evaluation across repeated runs and across different agent systems
- **formal scoring of permission compliance**, including refusal quality, redaction behavior, and role-boundary adherence
- **trace-based evaluation** of multi-step agent behavior, including tool selection, argument correctness, evidence grounding, and execution efficiency
- **energy- and facility-aware tasks** as first-class benchmark components rather than optional extensions

This is the central gap ExaBench addresses.

---

## ExaBench’s Innovation

ExaBench is not merely a dataset of HPC questions. It is a **benchmark framework** for evaluating HPC agent systems under realistic operational conditions.

Its innovation lies in combining five ideas that are usually studied separately:

### 1. HPC-Native Benchmarking

ExaBench is designed specifically for the HPC domain, where agents must reason over schedulers, jobs, performance signals, telemetry streams, documentation, and infrastructure policies rather than generic web or enterprise interfaces.

### 2. Role-Aware Evaluation

The benchmark models the fact that HPC environments are inherently multi-role. A researcher, a normal user, a sysadmin, and a facility operator may ask related questions but require different answers, different evidence, and different access levels. ExaBench therefore evaluates whether agents respond **correctly and appropriately for the requesting role**.

### 3. Deterministic State-Snapshot Evaluation

Instead of relying on live clusters, ExaBench evaluates agents against replayable HPC state snapshots. This makes experiments reproducible, comparable, and suitable for scientific reporting.

### 4. Trace-Based Scoring

ExaBench evaluates not only final answers, but also the interaction process: which tools the agent invoked, whether arguments were correct, whether the evidence matched the environment state, and whether the reasoning remained within policy boundaries.

### 5. Governance- and Energy-Aware Assessment

Unlike most existing benchmarks, ExaBench treats **RBAC compliance, safe refusal, and energy/facility reasoning** as core benchmark dimensions rather than peripheral concerns.

---

## Scientific Contribution

From a research perspective, ExaBench contributes:

1. **A new benchmark domain:** HPC agent systems
2. **A role-aware task model:** evaluation conditioned on stakeholder role and permission profile
3. **A deterministic replay environment:** reproducible HPC telemetry and policy evaluation
4. **A trace-based protocol:** scoring both final outcomes and agent trajectories
5. **A multi-dimensional scorecard:** accuracy, tool correctness, grounding, compliance, robustness, latency, and cost
6. **A bridge between HPC and agentic evaluation research:** connecting operational supercomputing needs with modern benchmark methodology

---

## What Makes ExaBench Distinct

The closest existing methodological analogue is **Cloud-OpsBench**, which shows the value of deterministic operational-state evaluation, but its focus is cloud root-cause analysis rather than HPC operations. Similarly, **τ-bench** demonstrates policy-aware interactive evaluation, but not in infrastructure-heavy HPC contexts. Tool-use and trace-based benchmarks contribute scoring ideas, but they do not model HPC-native environments or multi-role operational support.

ExaBench distinguishes itself by bringing these benchmark principles together in a single framework centered on **HPC operations, telemetry reasoning, policy sensitivity, and role-aware decision support**.

---

## Positioning Statement

For consistency with the project framing, ExaBench v0.1 is canonically defined as a role-aware, tool-using, permission-aware, trace-based, and reproducible benchmark framework grounded in deterministic environment snapshots.

> **ExaBench is a benchmark framework for evaluating HPC agent systems using role-aware tasks, deterministic HPC state snapshots, and trace-based scoring.**
> 

---

## Concise Novelty Claim

In one sentence, the novelty of ExaBench is:

> **ExaBench is the first benchmark framework, to our knowledge, that unifies HPC-native tools, role-aware tasks, deterministic operational snapshots, and trace-based evaluation for AI agent systems in HPC environments.**
> 

---

## Closing Statement

ExaBench therefore shifts the evaluation target from “can an LLM answer HPC questions?” to a much stronger and more practical question: **can an AI agent operate reliably, safely, and efficiently in HPC environments under realistic tool, policy, and role constraints?**