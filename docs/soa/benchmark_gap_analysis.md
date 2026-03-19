# ExaBench Gap Analysis

> Generated: 2026-03-19 from 17 extracted resource cards

---

## Summary: What Is Missing for HPC

The following gaps appear consistently across all surveyed resources:

- **role-aware** — missing in: agentarch, bfcl, clear, cloud-opsbench, dacomp, infiagent-dabench, llm-agents-workflow-provenance, toolbench, worfbench
- **SLURM** — missing in: agentarch, agentbench, cloud-opsbench, infiagent-dabench, scienceagentbench, tau-bench, toolbench, trail
- **RBAC** — missing in: agentbench, clear, cloud-opsbench, dacomp, llm-agents-workflow-provenance, scienceagentbench, toolbench, trail
- **HPC monitoring** — missing in: agentarch, cloud-opsbench, infiagent-dabench, scienceagentbench, tau-bench, toolbench
- **telemetry** — missing in: agentbench, clear, dacomp, tau-bench, tau2-bench, trail
- **HPC-native** — missing in: cloud-opsbench, dacomp, infiagent-dabench, tau-bench, tau2-bench, worfbench
- **energy** — missing in: cloud-opsbench, llm-agents-workflow-provenance, tau-bench, toolbench, trail
- **multi-role** — missing in: cloud-opsbench, scienceagentbench, tau-bench
- **scheduler** — missing in: dacomp, llm-agents-workflow-provenance, tau2-bench
- **HPC energy monitoring** — missing in: cloud-opsbench, infiagent-dabench

---

## Per-Resource Gap Details

### agentarch

Enterprise tasks with no HPC specificity. No SLURM, HPC monitoring, or role-aware evaluation. Architecture findings may not transfer to HPC domain.

### agentbench

Domain-agnostic and role-blind — no SLURM, no telemetry, no RBAC, no role-specific task variants. Measures general capability not operational correctness.

### agentops

General observability tool — no HPC semantics, no benchmark task evaluation, no ground truth or scoring logic.

### bfcl

No HPC tool signatures, no multi-step HPC workflows, no role-aware evaluation (tool access varies by role), no environment state context.

### clear

No HPC-specific tool use evaluation, no role-aware assurance dimension (RBAC), no telemetry reasoning evaluation, no HPC environment. Framework is methodology-only without runnable tasks.

### cloud-opsbench

No HPC-native tools (SLURM, HPC monitoring, facility energy monitoring), no role-aware evaluation (same snapshot answered differently per role), no multi-role task variants, no energy monitoring reasoning, no policy/RBAC compliance scoring

### dacomp

No HPC-native data formats, no role-aware task variants, no RBAC evaluation, no real-time telemetry reasoning. Enterprise data context does not map to HPC scheduler or monitoring systems.

### flowcept

Flowcept is a provenance tool, not a benchmark. It does not define tasks, ground truth, or scoring. It needs to be paired with ExaBench's task and scorer layers to form a complete evaluation system.

### infiagent-dabench

No HPC-native data formats (HPC monitoring, facility energy, SLURM accounting), no multi-step tool orchestration beyond code execution, no role-aware task variants, no policy compliance evaluation.

### langfuse

Langfuse is a general observability tool, not an HPC benchmark. It captures what happened but does not define tasks, ground truth, or HPC-specific evaluation logic.

### llm-agents-workflow-provenance

No role-aware evaluation (same query answered differently per role), no RBAC compliance scoring, limited to workflow provenance (not full HPC operational scope: scheduler, energy, security policy).

### scienceagentbench

Scientific workflow context is unrelated to HPC operations. No SLURM, HPC monitoring, RBAC, or multi-role evaluation.

### tau-bench

No HPC-native tools (SLURM, HPC monitoring, telemetry), no role-based access control as a first-class metric, no multi-role task variants, no deterministic HPC environment snapshots, no energy/cost telemetry reasoning

### tau2-bench

No HPC-native tools, no role-based access control, no telemetry or scheduler state. Domain is customer service, not operational HPC.

### toolbench

Generic REST APIs have no HPC semantics. No SLURM, HPC monitoring, RBAC, or energy monitoring. No role-aware access control. Breadth (16k APIs) is the opposite of ExaBench's depth-focused HPC tool evaluation.

### trail

Taxonomy covers general agentic errors, not HPC domain-specific failures. No SLURM command errors, telemetry query failures, energy calculation drift, RBAC violations, or role-inappropriate explanations. No HPC environment context in traces.

### worfbench

No HPC-native scenarios, no tool-use evaluation within workflow steps, no environmental state changes between steps, no role-aware workflow variants.
