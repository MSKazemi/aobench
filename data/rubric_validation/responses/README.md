# Rubric Validation Responses

50 synthetic HPC response files for rubric judge validation.

## File naming

| Prefix | Rubric template | Count |
|--------|----------------|-------|
| `rv_job_*` | `hpc_job_failure_diagnosis_v1` | 20 |
| `rv_energy_*` | `hpc_energy_anomaly_v1` | 15 |
| `rv_rbac_*` | `hpc_rbac_response_v1` | 15 |

## Quality tier distribution

| Tier | Target % | Files |
|------|---------|-------|
| poor | 30% | rv_job_001–006, rv_energy_001–005, rv_rbac_001–004 |
| moderate | 40% | rv_job_007–014, rv_energy_006–011, rv_rbac_005–010 |
| good | 30% | rv_job_015–020, rv_energy_012–015, rv_rbac_011–015 |

## Source method per quality tier

| Tier | Source |
|------|--------|
| poor | Deliberately degraded: missing root cause, hallucinated metrics, wrong diagnosis |
| moderate | LLM-generated (partially correct, incomplete evidence) |
| good | Expert-written exemplars with full evidence citations |

## JSON schema

```json
{
  "response_id": "rv_job_001",
  "rubric_id": "hpc_job_failure_diagnosis_v1",
  "task_context": "...",
  "task_question": "...",
  "agent_response": "...",
  "quality_tier": "poor | moderate | good"
}
```
