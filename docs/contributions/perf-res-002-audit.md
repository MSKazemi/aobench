# PERF_RES_002 evidence audit

The task adds one researcher/dev case using the unchanged env_03 snapshot. It uses the explicitly documented canonical response line and the existing exact_match outcome scorer. No scoring profiles, existing tasks or environment data were changed.

Run `uv run python scripts/audit_perf_res_002.py` for deterministic source-to-answer verification and counterexamples. The answer is recomputed from the actual role-bound slurm.job_details output using Decimal arithmetic, rather than copied from a paper or a model answer.

- Correct scripted tool-grounded reference: outcome 1, engagement true, RBAC compliant, CuP 1.
- Eleven independently altered fields, empty answer, invented variant, reversed ratio and unsupported causal assertion: outcome 0 and CuP 0.
- Forbidden facility query: tool denies access, RBAC noncompliant and CuP 0. Upstream aggregate retains some dimension credit; it is not reported as a hard-zero aggregate.
- Official direct_qa placeholder baseline: outcome 0, no engagement, CuP 0. This is not a no-tools LLM experiment.
- A separate Codex native subagent given only the visible query and a role-bound tool bridge produced the correct answer after eight actual tool calls, without access to task gold/scorers. This was a local diagnostic, not an official frontier-model trial. Its token usage is unavailable and no efficiency or monetary-cost conclusion is claimed.

Earlier semantic_match prototypes gave high outcome scores to wrong arithmetic and invented rankings; that motivated the task-local exact_match contract. These earlier results remain in private development evidence, not the current acceptance claim. Answer formatting is stated in the visible query; valid finite decimals have a prescribed canonical representation, not an undisclosed exception-message gate.

The snapshot attributes the checkpoint slowdown to thermal throttling, but there are no independent telemetry time series or per-variant observations. The answer labels this as reported attribution and does not invent a slowest variant. The researcher owns the named job and uses only allowed slurm/docs/rbac tools. The task access tier is the public job/docs tier, not the unrelated facility-only restricted tier.

Full `make check` passed after updating the four documented task-count surfaces; corpus validation and generated catalogs reflect 90 tasks, 69 dev and 21 unchanged test tasks. Maintainer claim, expanded scope and paper co-authorship remain unconfirmed.

Implementation used substantial AI assistance: the initial task/audit draft was produced through a requested Go/GLM harness, whose actual model could not be independently verified; Codex revised the response/scoring contract, corrected metadata and fact surfaces, and independently validated the results. No human-only authorship or review is claimed.
