## 🧩 **Key–Value Use Cases in the HPC Agent Benchmark**

| Key                     | Purpose / Use Case in Benchmark                                                                                                                               | Typical Example                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **`query_id`**          | Unique identifier for each benchmark query — enables traceability, cross-referencing, evaluation reporting, and deduplication.                                | `"Q-ENERGY-042"` — easily searchable in logs and result tables.                       |
| **`user_type`**         | Defines **persona context** for the query (e.g., HPC user, sysadmin). Used to test how well the agent tailors responses to different roles and privileges.    | `"System Administrator"` — implies deeper data access, different expectations.        |
| **`category`**          | Groups queries into **functional domains** for coverage metrics and analytics (e.g., Energy, Jobs, Storage). Helps measure model performance per area.        | `"Energy & Power"` — can later analyze accuracy/recall on all energy-related queries. |
| **`intent`**            | Short description of the *underlying goal or meaning* behind the query — critical for intent detection and semantic clustering evaluation.                    | `"Cluster energy trend over time"` — ground-truth semantic label.                     |
| **`query_text`**        | The actual **user-facing text** sent to the HPC agent. This is what the LLM or retrieval system will process.                                                 | `"Show total energy per rack and node for 2023–2024 with daily granularity."`         |
| **`data_sources`**      | Indicates which telemetry, logs, or datasets are needed to answer the query. Used for data-access simulation, RAG grounding, and dependency coverage metrics. | `["IPMI","Prometheus"]` — benchmark whether the agent knows which APIs to call.       |
| **`difficulty`**        | Qualitative measure of query complexity. Used to build tiered test sets (easy/medium/hard/edge) and to analyze model degradation with harder tasks.           | `"medium"` — multi-source but simple aggregation.                                     |
| **`priority`**          | Indicates **operational importance** or **evaluation weighting**. You can give higher weight to “critical” queries during scoring.                            | `"high"` — gets higher benchmark weight or QA priority.                               |
| **`tags`**              | List of **keywords** or **semantic anchors** for filtering, clustering, and tagging analytics. Enables grouping and model fine-tuning later.                  | `["energy","time-series","admin"]` — used in dashboard filters.                       |
| **`expected_answer`**   | Specifies **expected output format or type** (table, chart, fact, explanation). Used for validating output structure and UI tests.                            | `"table"` — correct answer should be tabular.                                         |
| **`evaluation_signal`** | Defines **how correctness is evaluated** (e.g., range check, trend direction, exact match, heuristic). Powers your scoring pipeline.                          | `"range_check(sum_kWh)"` — output must be within expected range.                      |
| **`dependencies`**      | Lists external elements or preconditions required to answer (e.g., data mapping, configs). Useful to simulate missing-data scenarios or dependency injection. | `["rack_node_mapping"]` — ensures agent handles lookups gracefully.                   |
| **`dedupe_of`**         | Used for **deduplication tracking** — references another query if this one was derived or merged. Keeps dataset clean and explainable.                        | `null` — not a duplicate; or `"Q-ENERGY-010"` if merged.                              |
| **`created_at`**        | Timestamp for dataset versioning and provenance tracking. Useful for incremental benchmark releases and temporal analysis.                                    | `"2025-11-01T18:30:00Z"`                                                              |
| **`notes`**             | Freeform space for **annotations** (limitations, rationale, special scoring rules). Helps reviewers and future maintainers understand context.                | `"Needs rack map"` — clarifies why dependency exists.                                 |

---

## 🎯 **How These Keys Work Together**

| Benchmark Function                     | Keys Involved                                      | Example Use                                                                  |
| -------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Coverage Analysis**                  | `category`, `user_type`, `difficulty`              | Ensure each role × domain × tier has sufficient queries.                     |
| **Evaluation & Scoring**               | `expected_answer`, `evaluation_signal`, `priority` | Automated benchmark scripts know how to grade each query and assign weights. |
| **RAG Data Simulation**                | `data_sources`, `dependencies`                     | Inject only the relevant documents/metrics to test retrieval accuracy.       |
| **Deduplication & Evolution Tracking** | `query_id`, `dedupe_of`, `created_at`              | Manage dataset growth and versioning.                                        |
| **Role-Aware Prompt Evaluation**       | `user_type`, `intent`, `query_text`                | Test whether the agent adjusts tone, scope, and access correctly.            |
| **Dataset Analytics / Dashboarding**   | `tags`, `priority`, `difficulty`                   | Build dashboards: “How well do we handle Energy vs. Jobs?”                   |
| **Documentation & Review**             | `notes`                                            | Communicate manual observations or caveats to evaluators.                    |


