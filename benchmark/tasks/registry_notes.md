# ExaBench Operational Task Registry (v0.1)

This artifact package contains a seed operational task registry for early ExaBench development.

## Included files

- `registry.csv` — machine-readable task index
- `task_specs/*.json` — per-task execution specs (e.g. JOB_USR_001.json, MON_SYS_001.json)
- Original exports: `../exabench_operational_task_registry_v0_1_seed.xlsx`, `../exabench_operational_task_registry_v0_1_seed.csv`

## Recommended format strategy

For the early version:

- **Authoring / curation:** Notion flat table
- **Machine-readable export:** CSV
- **Later execution packaging:** JSON or YAML per task if needed

## Why this format

This keeps the registry:

- easy to edit in Notion
- easy to filter and review
- easy to export into Python / pandas
- simple enough for 10–30 seed tasks

## Notes

The current rows are starter seed records. Before calling the registry benchmark-ready, replace placeholder values for:

- `environment_id`
- `gold_evidence_refs`
- readiness fields such as `validation_status`, `gold_evidence_status`, and `scoring_readiness`
- `split_assignment`
