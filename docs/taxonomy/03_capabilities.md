# 03 — Capabilities

Owner: Mohsen

### Purpose

This page defines the **capability dimension** of the ExaBench taxonomy: what an agent must be able to do (independent of persona, task category, or policy constraints).

### Capability groups

- **Retrieval grounding**
    - cite and ground answers in the provided knowledge sources
    - handle missing or conflicting sources
- **Telemetry querying**
    - formulate metric, log, and event queries
    - choose correct source and time window
- **Cross-source fusion**
    - combine docs with telemetry
    - correlate multi-modal signals (metrics + logs + tickets)
- **Diagnostic reasoning**
    - generate hypotheses
    - rank likely causes and propose checks
- **Optimization recommendation**
    - propose performance and energy improvements
    - quantify trade-offs and constraints
- **Role-aware response**
    - adapt scope, tone, and detail to persona
    - expose only role-appropriate information
- **Permission compliance**
    - enforce RBAC and tier constraints
    - refuse or redact when access is insufficient
- **Incident handling**
    - triage alerts
    - propose escalation and containment steps
- **Energy-awareness**
    - reason about power, thermals, PUE
    - propose sustainability-aware actions
- **Action planning**
    - propose step-by-step plans
    - decide which tools to use and in what order