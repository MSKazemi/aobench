# AOBench Roadmap

Status of the multi-surface benchmark platform.

**Want to help?** Every item below that isn't shipped has a tracking issue.
Browse them by effort — [`effort: small`](https://github.com/MSKazemi/aobench/labels/effort%3A%20small)
is the best place to start — or by area, or pick from
[**good first issues**](https://github.com/MSKazemi/aobench/labels/good%20first%20issue).
Work is grouped into [milestones](https://github.com/MSKazemi/aobench/milestones).

Legend: ✅ shipped · 🟡 partial (usable core shipped, sub-feature deferred) · ⛔ deferred (external dependency).

<!--roadmap-start-->
<!--roadmap-status-start-->

## Current status

_Last updated (UTC): 2026-11-19 20:47_

- **Latest release:** [v0.4.1](https://github.com/MSKazemi/aobench/releases/tag/v0.4.1) (2026-08-08).
- **Corpus on `main`** (generated `benchmark/BENCHMARK_FACTS.json`, package version 0.4.1): 90 tasks (69 dev / 21 held-out test), 29 environments, 10 QCATs, 5 roles, 7 weighted scoring dimensions.
- **Open issues:** 44 — [all issues](https://github.com/MSKazemi/aobench/issues) · [milestones](https://github.com/MSKazemi/aobench/milestones).

### [Blocked — external dependency](https://github.com/MSKazemi/aobench/milestone/4)

0 of 2 closed · no due date.

| Issue | Title |
|---|---|
| [#18](https://github.com/MSKazemi/aobench/issues/18) | F8 — adopt the async MCP Tasks primitive once it stabilises |
| [#19](https://github.com/MSKazemi/aobench/issues/19) | F18/F19 — containerized HPC terminal runner with a tiered sandbox |

### [v0.5 — Contributor on-ramp & DX](https://github.com/MSKazemi/aobench/milestone/1)

16 of 23 closed · no due date.

| Issue | Title |
|---|---|
| [#7](https://github.com/MSKazemi/aobench/issues/7) | Pay down the mypy --strict debt so the CI type-check step can stop being advisory |
| [#9](https://github.com/MSKazemi/aobench/issues/9) | Record a 30-second demo GIF for the README |
| [#23](https://github.com/MSKazemi/aobench/issues/23) | Triage the 96 CodeQL findings — path injection on the server surfaces first |
| [#26](https://github.com/MSKazemi/aobench/issues/26) | Write a second task for a thin QCAT × role cell (32 of 50 have only one) |
| [#27](https://github.com/MSKazemi/aobench/issues/27) | Run a model and submit a leaderboard entry — negative results welcome |
| [#113](https://github.com/MSKazemi/aobench/issues/113) | SECURITY.md says AOBench has no network services or authentication, but it ships REST and MCP servers with API-key auth |
| [#114](https://github.com/MSKazemi/aobench/issues/114) | Docs on main present the v0.4.1 corpus (88 tasks, 67 dev) as current while generated facts say 90 / 69, and ROADMAP still shows v0.4 in progress |

### [v0.6 — Infrastructure](https://github.com/MSKazemi/aobench/milestone/2)

0 of 9 closed · no due date.

| Issue | Title |
|---|---|
| [#10](https://github.com/MSKazemi/aobench/issues/10) | F2 — durable async run queue (arq/Redis worker) |
| [#11](https://github.com/MSKazemi/aobench/issues/11) | F3 — outbound webhooks for run lifecycle events |
| [#12](https://github.com/MSKazemi/aobench/issues/12) | F4 — generated typed client SDK from the OpenAPI schema |
| [#13](https://github.com/MSKazemi/aobench/issues/13) | F5 — persist experiment results in a database |
| [#14](https://github.com/MSKazemi/aobench/issues/14) | F7 — full OIDC to RBAC mapping for the MCP server |
| [#15](https://github.com/MSKazemi/aobench/issues/15) | F12 — live A2A HTTP transport |
| [#33](https://github.com/MSKazemi/aobench/issues/33) | LiteLLM adapter — one file, ~100 providers |
| [#34](https://github.com/MSKazemi/aobench/issues/34) | Google Gemini adapter |
| [#35](https://github.com/MSKazemi/aobench/issues/35) | AWS Bedrock adapter |

### [v0.7 — Reporting & scoring depth](https://github.com/MSKazemi/aobench/milestone/3)

0 of 2 closed · no due date.

| Issue | Title |
|---|---|
| [#16](https://github.com/MSKazemi/aobench/issues/16) | [Epic] Reporting suite — report renderers on the data→stats→model→render pipeline |
| [#17](https://github.com/MSKazemi/aobench/issues/17) | F30 — thermal digital-twin surrogate for facility-aware scoring |

### Not yet in a milestone

| Issue | Title |
|---|---|
| [#20](https://github.com/MSKazemi/aobench/issues/20) | Start here — where to contribute |
| [#60](https://github.com/MSKazemi/aobench/issues/60) | [Result] Claude Sonnet Benchmarking |
| [#62](https://github.com/MSKazemi/aobench/issues/62) | Verify every command in the docs actually does what the page says — from a clean checkout |
| [#63](https://github.com/MSKazemi/aobench/issues/63) | Two dev-split tasks are unpassable: `my own job` is owned by someone else, so a correct agent is RBAC hard-failed |
| [#72](https://github.com/MSKazemi/aobench/issues/72) | Flaky release gate: test_report_json_flag_emits_clean_json_on_stdout fails ~1 run in 8 |
| [#74](https://github.com/MSKazemi/aobench/issues/74) | Ten tasks grant tool families that do not exist — three dev tasks get zero tools, and validate passes |
| [#85](https://github.com/MSKazemi/aobench/issues/85) | Generate and send a real RBAC-hard-fail fixture to the EvalPort spec (discussion #51) |
| [#89](https://github.com/MSKazemi/aobench/issues/89) | [Result] qwen3.5:9b (Ollama, Q4_K_M, local M2 Pro): 0.561 over 3 runs |
| [#91](https://github.com/MSKazemi/aobench/issues/91) | An unknown tool name is scored as an RBAC hard fail, and malformed tool arguments drop the task |
| [#96](https://github.com/MSKazemi/aobench/issues/96) | [EPIC][HF] Hugging Face Hub integration — dataset, verified leaderboard, safety arena, traces and OpenEnv |
| [#97](https://github.com/MSKazemi/aobench/issues/97) | [HF-01][P0] Audit release eligibility, locked split, corpus facts, licensing and score integrity |
| [#98](https://github.com/MSKazemi/aobench/issues/98) | [HF-02][P0] Define canonical Hub artifact schemas, immutable fingerprints and comparability rules |
| [#99](https://github.com/MSKazemi/aobench/issues/99) | [HF-03][P0] Build deterministic development/lite dataset exporter with strict test-leakage and privacy guards |
| [#100](https://github.com/MSKazemi/aobench/issues/100) | [HF-04][P0] Publish a versioned AOBench Dataset Card and safe opt-in Hugging Face upload workflow |
| [#101](https://github.com/MSKazemi/aobench/issues/101) | [HF-05][P0] Build evidence-verified, version-pinned leaderboard snapshot feed |
| [#102](https://github.com/MSKazemi/aobench/issues/102) | [HF-06][P1] Build responsive static Hugging Face AOBench Leaderboard Space |
| [#103](https://github.com/MSKazemi/aobench/issues/103) | [HF-07][P1] Build interactive HPC Safety Arena with role-aware RBAC demonstration |
| [#104](https://github.com/MSKazemi/aobench/issues/104) | [HF-08][P1] Convert reviewed AOBench traces to Hub Session Traces Format (STS) with redaction |
| [#105](https://github.com/MSKazemi/aobench/issues/105) | [HF-09][P1] Document and test Hugging Face model evaluation path using existing AOBench adapters |
| [#106](https://github.com/MSKazemi/aobench/issues/106) | [HF-10][P1] Integrate Hugging Face docs, discoverability, CI validation and opt-in release automation |
| [#107](https://github.com/MSKazemi/aobench/issues/107) | [HF-11][P2] Prototype AOBench as a policy-aware OpenEnv/TRL interactive environment |
| [#108](https://github.com/MSKazemi/aobench/issues/108) | [HF-12][P2] Research protocol: disjoint HPC permission training data, SFT/GRPO experiments and anti-contamination evaluation |
| [#109](https://github.com/MSKazemi/aobench/issues/109) | [HF-13][P3] Evaluate native Hugging Face Benchmark registration and model .eval_results interoperability |
| [#110](https://github.com/MSKazemi/aobench/issues/110) | [HF-14][P1 Release] End-to-end Hub publication QA, security/privacy sign-off, crosslinks and rollout/rollback checklist |

_Generated by `scripts/gen_roadmap.py` (weekly workflow `roadmap-sync`); edit the issues, not this block. Priorities live on the project board._

<!--roadmap-status-end-->

## Shipped

### Core benchmark (v0.3)
- Task corpus over deterministic environment bundles, 5 roles, 10 QCATs, 12 scorers / 7 weighted dimensions
  (current counts in **Current status** above, generated from `benchmark/BENCHMARK_FACTS.json`).
- CLEAR scorecard (Cost / Latency / Efficacy / Assurance / Reliability).
- M100 ExaData-grounded environments and tasks.

### Multi-surface engine access (v0.4 — released in v0.4.0, 2026-07-23; v0.4.1, 2026-08-08)
Every surface calls the shared `BenchmarkService` façade — identical scores across transports.

| Surface | Status | Notes |
|---------|--------|-------|
| REST API (FastAPI) — `aobench serve rest` | ✅ | run/score/report/trace/compare/robustness/datasets + async jobs + SSE; API-key→role auth + rate limiting |
| FastMCP server — `aobench serve mcp` | ✅ | tools (`run_task`/`score_trace`/`validate_benchmark`/`robustness`) + `aobench://` resources; JWT auth hook |
| A2A evaluation | ✅ | Agent-Card conformance + delegation / comms-cost / attribution / lifecycle / card-poisoning scorers |
| CLI / terminal evaluation | ✅ | mock Slurm shims, destructive-command guard, end-state verifier |

### Cross-cutting (v0.4)
- OTel-GenAI trace exporter · deterministic replay cassettes · in-toto attestation.
- Carbon/cost/CO₂e accounting + contamination guard · pass^k + bootstrap CIs (measurement rigor).
- Futuristic HPC scorers: incident RCA (+ log evidence), escalation/abstention, carbon-aware
  scheduling, predictive maintenance.
- MCP-usage scorers: tool-selection, injection-resistance, elicitation.

## In progress / partial (🟡)

| Item | Shipped | Deferred half |
|------|---------|---------------|
| Async run queue (F2) | job registry + async submission (single process) | durable arq/Redis worker — [#10](https://github.com/MSKazemi/aobench/issues/10) |
| Event delivery (F3) | SSE + polling | outbound webhooks — [#11](https://github.com/MSKazemi/aobench/issues/11) |
| Typed SDK (F4) | REST auth + OpenAPI | generated client SDK — [#12](https://github.com/MSKazemi/aobench/issues/12) |
| Datasets/Experiments API (F5) | datasets read side | experiment-result persistence DB — [#13](https://github.com/MSKazemi/aobench/issues/13) |
| MCP auth (F7) | JWT scaffold | full OIDC → RBAC mapping — [#14](https://github.com/MSKazemi/aobench/issues/14) |
| A2A access (F12) | adapter core (injected transport) | live A2A HTTP transport — [#15](https://github.com/MSKazemi/aobench/issues/15) |
| CLI access (F19) | adapter core (injected executor) | Docker/gVisor executor — [#19](https://github.com/MSKazemi/aobench/issues/19) |
| Futuristic HPC (F30) | carbon-aware + predictive-maintenance scorers | thermal digital-twin surrogate — [#17](https://github.com/MSKazemi/aobench/issues/17) |

## Deferred — external dependency (⛔)

- **F8** — async MCP Tasks primitive (experimental in MCP 2025-11-25) — [#18](https://github.com/MSKazemi/aobench/issues/18).
- **F18** — containerized HPC terminal runner + tiered sandbox (needs a sandboxing dependency) — [#19](https://github.com/MSKazemi/aobench/issues/19).

## Next milestones

Live milestone progress and every open issue are listed in **Current status** above, regenerated
from GitHub by a weekly workflow. The themes, in priority order:

1. **Benchmark integrity** — unknown tool names scored as RBAC hard fails ([#91](https://github.com/MSKazemi/aobench/issues/91)),
   unpassable own-job tasks ([#63](https://github.com/MSKazemi/aobench/issues/63)), tool families that do not
   exist ([#74](https://github.com/MSKazemi/aobench/issues/74)), the flaky release gate ([#72](https://github.com/MSKazemi/aobench/issues/72)).
   Fixes that move published scores ship with an explicit scoring-version note.
2. **Hugging Face Hub integration** — dataset, verified leaderboard, safety arena — epic [#96](https://github.com/MSKazemi/aobench/issues/96).
3. **Infra features** as dependencies come online: Redis worker (F2), Docker sandbox (F18/F19),
   live A2A transport (F12), experiment DB (F5), OIDC (F7), SDK codegen (F4), thermal twin (F30).
4. **Reporting suite** — report renderers on the data→stats→model→render pipeline — [#16](https://github.com/MSKazemi/aobench/issues/16).
5. **Strict typing** — make the CI type check blocking — [#7](https://github.com/MSKazemi/aobench/issues/7).

<!--roadmap-end-->