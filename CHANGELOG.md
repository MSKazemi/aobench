# Changelog

## Unreleased

### Added — comparison example

- **`examples/05_compare_two_adapters.py`** runs the same offline task through two
  `direct_qa` configurations and reuses `aobench compare runs` to show their
  per-dimension deltas, including governance. It gives new users a runnable starting
  point for the core workflow: compare two systems before trusting an aggregate score.

### Added — `--json` for `report json` and `compare runs`

- **`aobench report json <run_dir> --json`** and **`aobench compare runs <a> <b>
  --json`** now print the underlying summary/diff object as a single JSON value on
  stdout, with no banner and no human-readable table — the same convention every
  `aobench list` subcommand already uses. Wiring either command into a CI step
  previously meant scraping formatted text; both now pipe cleanly into `jq` or any
  JSON consumer. Default (no flag) output is unchanged.
- **`compare runs` JSON now carries `hard_fail_count_a` / `hard_fail_count_b`.** The
  human table has always printed the absolute hard-fail counts, but the diff object
  carried only the `new_hard_fails` / `resolved_hard_fails` deltas, and the absolute
  count was not derivable from the task rows. Since a hard fail is an RBAC violation
  that zeroes a task's aggregate score, that is the field a CI governance gate keys
  on. Additive — existing keys are unchanged, and this applies to the `--output` file
  as well as to `--json`.

### Fixed — `aobench clear run <dir>` did not work as documented

- **`aobench clear run data/runs/<run_id>` errored.** That positional form is what
  five public documentation pages show — installation, reproducing results, use cases,
  the leaderboard guide, and the system-architecture reference — but the command only
  accepted `--run-dir`, so every reader who copy-pasted it hit
  `Missing option '--run-dir' / '-d'`. Run directories may now be given positionally,
  with `--run-dir`, or both mixed for multi-model comparison; the forms are equivalent.
  Invoking it with no run directory at all now prints an actionable message naming both
  forms and how to list available runs, and exits 2 instead of showing a usage dump.
  Four regression tests cover it.

### Added — contributor on-ramp

- **`AGENTS.md`** — a public [README for coding agents](https://agents.md/): the
  architecture map, exact build/test/lint commands, the invariants that must not be
  broken (determinism, no network in tests, read-only snapshots, RBAC enforcement, the
  held-out `test` split), and what must not be changed without a design discussion.
  `.github/copilot-instructions.md` is a thin pointer to it rather than a second copy.
- **An AI-assistance policy** in `CONTRIBUTING.md`: assistance is welcome, the bar is
  that you understand the change, have run `make check`, and disclose substantial help.
- **A demo recording** in the README (`docs/assets/demo.gif`), rendered from verbatim
  captured output of a real offline run — one Marconi100-grounded task through the
  zero-tool baseline, then the CLEAR scorecard, with no cluster and no API key.
- The README contributing section now leads with the two contributions that need no
  code and no hardware — authoring a task, and submitting an independent evaluation
  result — and links `AUTHORS.md`, where every merged contribution earns a line.

### Fixed — contributor-facing documentation

- `CONTRIBUTING.md` claimed Python 3.11+; the project requires 3.10+ (`pyproject.toml`).

### Added — visual identity

- **A logo and brand system.** `docs/assets/logo.svg` — a 3×3 grid of compute nodes
  with an agent's ordered trace running through it to the scored end state. Deep navy
  `#1a237e`, indigo `#3949ab`, amber `#ff8f00` for the trace. Wired in as the docs-site
  logo and favicon.
- **README hero banner**, light and dark (`banner-light.svg` / `banner-dark.svg`),
  served through `<picture>` so it follows the reader's GitHub theme, and linked
  straight to the documentation site.
- **A "How it works" diagram** in the README — task spec + snapshot → runner → agent ↔
  mock tools → trace → 12 scorers → CLEAR scorecard, rendered natively by GitHub.
- **Rebuilt social preview card** (1280×640) in the new brand, with
  `social-preview.svg` kept alongside it so the PNG can be regenerated when the numbers
  change. Brand assets, colours, and usage rules are documented in the press kit.
- Docs site polish: gradient hero with the logo, a corpus stat strip, hover-lifted
  cards, sticky navigation tabs, code-copy buttons, search suggestions, and Inter /
  JetBrains Mono.

### Fixed — the docs site was unreadable in dark mode

- The homepage hero hard-coded a light background (`#e8eaf6`) and navy text, and the
  table header row did the same, so both inverted badly under the slate (dark) theme.
  Every colour is now a CSS custom property defined for **both** schemes.
- The `.stat-strip` and contributor-`.wall` grids never applied: Material ships
  `.md-typeset ul:not([hidden]) { display: flow-root }`, whose `:not([attr])` component
  outranks a plain `.md-typeset .wall` selector, so both rendered as plain bulleted
  lists. The selectors now match Material's own shape and win.
- The navy brand colour never reached the header or links — Material's
  `[data-md-color-primary=indigo]` rules beat the `:root` overrides in `extra.css`. The
  palette is now `primary: custom`, which is the supported way to make those overrides
  apply.

### Documentation link placement

- The README now opens with the banner linking to <https://mskazemi.com/aobench/>, a
  headline **"Read the documentation"** line, and a one-line nav row; the Documentation
  section is a grouped hub (start here / understand the benchmark / for researchers)
  pointing at the live site rather than at raw `docs/*.md` paths.

### Fixed — the documented scoring weights were wrong

- **AOBench scores seven weighted dimensions, not six.** The README, the docs site,
  `llms.txt`, and `docs/framework/scoring-dimensions.md` all described six dimensions
  and quoted `default_hpc_v01` as `outcome 0.30 · tool_use 0.20 · grounding 0.15 ·
  governance 0.20 · robustness 0.10 · efficiency 0.05`. The actual profile in
  `benchmark/configs/scoring_profiles.yaml` is `outcome 0.30 · tool_use 0.15 ·
  grounding 0.10 · governance 0.20 · robustness 0.10 · efficiency 0.05 · **workflow
  0.10**` — the `workflow` (WorfEval) dimension was omitted entirely and three of the
  six documented weights were wrong. **No scores change**: the code always used the YAML.
  What changes is that the documentation now matches what was computed, which matters to
  anyone who reproduced or compared a published AOBench number from the documented
  weights. The `alpha0_minimal`, `alpha1_grounding`, and `clear_v1` rows were also
  wrong and are corrected; `clear_v1` was undocumented.
- `scripts/check_facts.py` now asserts the documented weight row against the YAML, so
  this class of drift fails CI instead of surviving four releases.

### Fixed — corpus counts and stale surfaces

- `llms.txt` claimed 80 tasks and 26 environments; `docs/index.md` badges claimed
  version 0.1.0, 30 tasks, and 20 environments. All now read 88 / 29 / 0.4.1, checked
  in CI by `scripts/check_facts.py`.
- `src/aobench/__init__.__version__` was pinned at `0.1.0.dev0` while `pyproject.toml`
  said `0.4.1`. It now derives from installed distribution metadata, so the two cannot
  drift again — and `aobench --version` reports the real version.
- `aobench list envs` / `info` / `doctor` counted `benchmark/environments/_m100_reference`
  as an environment, reporting 30 bundles instead of 29.
- `aobench rbac ingest` required a full task corpus to resolve its root, so it failed
  against a directory containing only `environments/` — which is exactly what the
  command is for. It now resolves leniently via `resolve_bundle_root`.
- The docs site emitted a broken `gtag` call on every page from a `G-XXXXXXXXXX`
  analytics placeholder, and the announcement bar advertised v0.1.0 with a
  `/AOBench/`-prefixed link that 404s.
- README documentation table pointed at four paths that had moved
  (`docs/COMMANDS.md`, `docs/environments-overview.md`, and two others), and claimed
  9 sub-commands / 51 test files / 20 environments.

### Added — documentation for researchers

- **[Datasheet](https://mskazemi.com/aobench/latest/about/datasheet/)** (Gebru et al.
  structure) and **[benchmark card](https://mskazemi.com/aobench/latest/about/benchmark-card/)**
  (Mitchell et al.) — full provenance, composition, intended use, and out-of-scope use.
- **[Limitations](https://mskazemi.com/aobench/latest/about/limitations/)** — an explicit
  account of what AOBench cannot measure, including that a high score does **not**
  license production deployment.
- **[Comparison](https://mskazemi.com/aobench/latest/about/comparison/)** with SWE-bench,
  τ-bench, BFCL, AgentBench, GAIA, MLAgentBench, and OSWorld, including where AOBench
  is worse.
- **[Related work](https://mskazemi.com/aobench/latest/about/related-work/)** with a
  verified `docs/references.bib` (author lists, venues, pages, and DOIs checked against
  the publisher or arXiv record).
- **[Versioning and score-comparability policy](https://mskazemi.com/aobench/latest/about/versioning/)**,
  **[responsible use](https://mskazemi.com/aobench/latest/about/ethics/)**,
  **[FAQ](https://mskazemi.com/aobench/latest/about/faq/)**,
  **[use cases](https://mskazemi.com/aobench/latest/about/use-cases/)**,
  **[glossary](https://mskazemi.com/aobench/latest/reference/glossary/)**, and a
  **[press kit](https://mskazemi.com/aobench/latest/about/press-kit/)**.
- **Generated [task catalog](https://mskazemi.com/aobench/latest/reference/task-catalog/)
  and [environment catalog](https://mskazemi.com/aobench/latest/reference/environment-catalog/)**,
  derived from the corpus by `scripts/gen_catalog.py` and drift-checked in CI, so an
  inventory page can never again disagree with the corpus.
- **[Leaderboard](https://mskazemi.com/aobench/latest/leaderboard/)** page with explicit
  submission requirements — version, split, profile, dated model snapshot, run count,
  and hard fails reported separately.

### Added — contributor and governance surfaces

- `GOVERNANCE.md` (decision process, how to become a maintainer, scientific-integrity
  commitments), `MAINTAINERS.md` (including an honest list of unowned areas),
  `AUTHORS.md`, `RESEARCH.md` (16 open research questions), `CITATION.bib`,
  `.github/FUNDING.yml`.
- Issue templates for proposing a task, proposing an environment (with a sanitisation
  checklist for real facility data), and submitting a leaderboard result.
- Guides: [evaluate your own agent](https://mskazemi.com/aobench/latest/guides/evaluating-your-own-agent/),
  [CI integration](https://mskazemi.com/aobench/latest/guides/ci-integration/),
  [adding a task](https://mskazemi.com/aobench/latest/guides/adding-a-task/),
  [adding an environment](https://mskazemi.com/aobench/latest/guides/adding-an-environment/).
- `examples/` with four runnable scripts (issue #4) — all offline, all executed by
  `tests/test_examples.py` so a broken example fails the build.
- `.devcontainer/devcontainer.json` for one-click Codespaces onboarding.

### Added — discoverability

- `docs/robots.txt` explicitly allowing search and AI crawlers (Googlebot, Bingbot,
  OAI-SearchBot, ChatGPT-User, PerplexityBot, ClaudeBot, GPTBot, and others), with the
  sitemap declared.
- JSON-LD structured data on every page — `SoftwareSourceCode`, `Dataset`, `Person`
  (with ORCID `sameAs`), `WebSite` + `SearchAction`, `TechArticle`, `BreadcrumbList` —
  plus Google Scholar `citation_*` metadata so the docs resolve as a scholarly artifact.
- `llms.txt` expanded into a full documentation map, and kept byte-identical between the
  repository root and `docs/`.
- `scripts/seo_check.py` (88 assertions over 9 key pages) and a `docs-integrity`
  workflow running fact drift, catalog drift, strict docs build, SEO surfaces, example
  execution, and a weekly external-link sweep.
- `make facts-check`, `facts-update`, `catalog`, `catalog-check`, `docs-build`,
  `docs-serve`, `seo-check`; `make check` now includes the drift checks.

### Added — onboarding

- **`aobench quickstart`** — a zero-argument first run. It resolves the benchmark
  corpus, picks a representative task, runs it with the tool-free `direct_qa` adapter,
  prints the per-dimension scorecard with a plain-English gloss for each dimension, and
  names the next commands. No API key, no network, no cluster.
- **`aobench doctor`** / **`aobench info`** — installation diagnostics. `doctor` checks
  Python, package metadata, core imports, corpus resolution and size, and optional
  extras, with a suggested fix per failure; it exits non-zero only on *required*
  failures, so a laptop with no provider SDK still passes. `info --json` is the blob to
  paste into a bug report.
- **`aobench list`** — `tasks`, `envs`, `qcats`, `roles`, `adapters`, `profiles`, and
  `scorers`, all with `--json`, and `--ids-only` on `tasks`/`envs` for shell pipelines.
  Previously the only way to learn a valid task ID was to `ls` the corpus by hand.
- **`python -m aobench`** as an alias for the console script, for environments where it
  is not on `PATH`.
- `make quickstart`, `make doctor`, and `make install-dev`; `make install-core` now
  really installs core-only (`uv sync --no-dev`).
- Mistyped `--task` / `--env` values now print the closest matching IDs and a pointer to
  `aobench list`, instead of a stack trace.

### Fixed — CLI

- **"Did you mean" dropped the likeliest ID.** Suggestions were ranked by `difflib`
  alone, which scores every member of an ID family identically against a truncated
  ID — so `--task JOB_USR_00` answered *"did you mean JOB_USR_005, JOB_USR_004,
  JOB_USR_003?"* and omitted `JOB_USR_001`, with the three winners decided by heap
  order rather than by anything a user would recognise. Prefix matches now outrank
  fuzzy ones and each pass is sorted, so the answer is stable and starts where the
  user was typing. Found by [@erensh27](https://github.com/erensh27) in
  [#25](https://github.com/MSKazemi/aobench/pull/25), whose end-to-end CLI test
  (`tests/cli/test_error_messages.py`) is the regression guard.

### Fixed — installed-package usage

- **The documented quick start crashed on a non-checkout install.** `aobench.paths`
  (which resolves `$AOBENCH_BENCHMARK_ROOT` → checkout → corpus bundled in the wheel)
  was wired into `validate benchmark` only. Every other entry point treated the literal
  string `"benchmark"` as a CWD-relative path, so `aobench run task …` died with
  `FileNotFoundError: benchmark/tasks/specs/JOB_USR_001.json` outside a checkout.
  `run task`, `run all`, `robustness task`, `robustness all`, `rescore`, `rbac ingest`,
  and `validate tasks|snapshots|authoring` now all resolve the corpus.
- `tools/catalog_loader` and `tasks/context_builder` located `hpc_tool_catalog.yaml` and
  `tasks/guidelines/` by walking up from `__file__`, which only ever resolves in a source
  checkout. Both now use the shared resolver.
- `utils/fs.resolve_benchmark_root` was a second, divergent resolver that could not see
  bundled package data; it now delegates to `aobench.paths`.
- `aobench doctor` split its checks into required/optional **by list position**, so the
  four checks that disappear when the corpus is missing silently reclassified optional
  extras as required failures — exactly the path a broken install takes.

### Changed — CI

- `actions/checkout` 4 → 7 and `astral-sh/setup-uv` 4 → **`v9.0.0`** across `ci.yml` and
  `docs.yml`. setup-uv publishes no floating major tag beyond `v7` (dropped at v8.0.0 as
  supply-chain hardening), so it is pinned to the immutable release tag rather than a
  mutable major.

### Fixed — CI

- The docs deploy pushed `gh-pages` from a linked `git worktree`. checkout v6+ injects the
  token via `includeIf.gitdir:<repo>/.git`, which does not match a worktree's gitdir, so that
  push would have become unauthenticated — latent, because the step is a no-op while
  `llms.txt` is unchanged, and `docs.yml` never runs on a pull request. The push is now
  issued from the main worktree and runs unconditionally, so a broken token fails the run
  immediately.

## [0.4.1] — 2026-08-08

### Security

- `scripts/ollama_tunnel.py` no longer ships a real SSH host, username and port as module
  defaults. `MC_SSH_HOST` is now required with no default. The values remain in published
  history; removing them there requires a history rewrite.
- Removed references to maintainer-only paths from public files, and a local home-directory
  path from the M100 guide.

### Added

- `codemeta.json` (CodeMeta 3.0) and `.zenodo.json` so registries and Zenodo carry the same
  authors, ORCIDs, licence and keywords as `CITATION.cff`.
- Docs: **Cite AOBench** and **Reproducing results** pages.
- CodeQL workflow, Dependabot configuration, `CODEOWNERS`, and a social preview image.

### Fixed

- **`CITATION.cff` was missing co-author Andrea Bartolini entirely.** Both authors are now
  present with ORCIDs and affiliation.
- Corpus counts were understated across every public surface: 80 tasks / 26 environments →
  **88 / 29**; split 62 dev / 18 test → **67 / 21** (synthetic core 59 / 21).
- M100 `provenance.json` records cited the wrong first author for the ExaData dataset paper
  (Beneventi → **Borghesi**); corrected in the data and in the generator scripts.
- `CONTRIBUTING.md` instructed `cd AOBench` when the repository clones as `aobench`.
- `llms.txt` was published only under `/latest/` and 404'd at the discoverable path.

### Added — Installation & running guide (docs)

- New canonical **[Installation & Running](docs/getting-started/installation.md)** page
  consolidating all three ways to install and run AOBench: the Python package (uv/pip with
  the optional-extras matrix), the Docker CLI image (`docker build` / `make repro-docker`),
  and the Docker Compose service stack (`make stack-up` → Langfuse + leaderboard). Wired into
  the MkDocs nav under a new **Getting Started** section.

### Fixed — Documentation accuracy

- Corrected the advertised Python floor to **≥ 3.10** (matching `requires-python`) in the docs
  landing page badge and `README.md`; noted 3.12 is used in Docker/CI.
- Replaced the misleading `pip install "aobench[openai]"` PyPI-style command on the docs home
  with the real from-source install (AOBench is not yet published to PyPI).
- Repaired two broken cross-links in the serving tutorial (`ROADMAP.md` → GitHub blob,
  an internal design note → the in-docs system-architecture page); `mkdocs build
  --strict` now passes clean.

### Changed — Repo consolidation (2026-07-16)

- Consolidated the working tree; internal dataset-tooling path references were updated
  accordingly. No change to the published package, the benchmark corpus, or any API.

### Added — Multi-surface engine access (AOBench Futures, P0)

- **Service façade** (`aobench.service.BenchmarkService`): one transport-agnostic API
  (`submit_run`/`get_run`/`get_trace`/`get_report`/`score_trace`/`list_tasks`/`list_envs`/
  `compare`/`robustness`) wrapping the existing `BenchmarkRunner`, with a typed error
  hierarchy and an ADR-0005 reproducibility fingerprint. All new surfaces call it, so CLEAR
  scores never diverge across surfaces.
- **Benchmark-engine REST API** (`aobench.server.rest`, extra `aobench[rest]`): FastAPI app
  exposing `/v1/runs`, `.../trace`, `.../report`, `.../events` (SSE live trace), `/v1/score`,
  `/v1/compare`, `/v1/robustness`, `/v1/tasks`, `/v1/envs`, `/v1/datasets`; API-key→role auth,
  rate limiting, OpenAPI 3.1. Distinct from the submission-only leaderboard API.
- **FastMCP server** (`aobench.server.mcp`, extra `aobench[mcp]`): exposes the engine as MCP
  tools (`run_task`, `score_trace`, `validate_benchmark`, `robustness`) and resources
  (`aobench://catalog/tasks|envs`, `aobench://runs/{id}/report|trace`); JWT-auth hook for the
  HTTP transport. (AOBench-as-MCP-server, distinct from the existing MCP-client adapter.)
- **OTel-GenAI trace exporter** (`aobench.exporters.otel`, extra `aobench[otel]`): emits runs
  as OpenTelemetry GenAI spans (`gen_ai.*`) with an `aobench.*` extension namespace over OTLP
  (Langfuse-native); pure `Trace → spans` converter, content-capture gated, no-op when absent.
- **MCP elicitation-handling scorer + tool-scaling axis** (`aobench.scorers.mcp_scorers`,
  Feature 11): `score_elicitation_handling` scores whether an agent supplies a valid missing
  HPC parameter (partition/account/walltime) when the server elicits it, vs hallucinating a
  value or (correctly) abstaining on a truly unknowable one; `tool_scaling_retention` measures
  accuracy retention as decoy tools scale from a handful to dozens.
- **Futuristic HPC scorers** (`aobench.scorers.hpc_scorers`, Features 28 & 30): an incident
  root-cause-analysis scorer (`score_rca`) that credits correct root-cause-entity localization
  and mitigation, with mitigation credit gated on entity correctness (CFS); and a carbon-aware
  scheduling scorer (`score_carbon_aware_schedule`) that rewards shifting deferrable jobs to
  low-carbon-intensity windows within deadlines, normalized against the carbon-optimal schedule;
  and a predictive-maintenance scorer (`score_predictive_maintenance`) scoring failure
  predictions by lead-time-weighted precision/recall (earlier actionable warnings score higher);
  plus a log-analysis evidence sub-scorer (`score_log_evidence`, set-F1 over the log lines an
  agent cites as RCA evidence vs gold) with a `find_evidence_lines` regex helper.
- **Escalation + abstention scorer** (`aobench.scorers.escalation_scorer`, Feature 29): rewards
  correct human-escalation of irreversible/high-risk actions and abstention when a tool is
  missing or an action is RBAC-blocked; penalizes under-escalation (unilateral action) and
  over-escalation beyond a reviewer budget; a unilateral *critical* action is a hard-fail.
- **End-state verification scorer** (`aobench.cli_track.end_state`, Feature 21): Harbor-style
  grading that judges the final environment state (dot-path assertions over the post-run
  `slurm_state.json`, with critical assertions as hard-fails and optional weighting) rather than
  the agent's transcript — outcome-based scoring that resists reward-hacking.
- **CLI/shell agent adapter — pure core** (`aobench.cli_track.cli_adapter`, Feature 19):
  `build_cli_trace` translates a recorded shell command/output stream into the universal
  `Trace` (each command a `shell` tool-call step; a destructive command flags `hard_fail` via
  the Feature 22 guard), and `CLIAdapter(BaseAdapter)` runs it with an injected command source.
  The container executor (Feature 18, Docker/gVisor) plugs in as that source; the trace-building
  core is Docker-free and reuses the scorer layer unchanged.
- **CLI/terminal track** (`aobench.cli_track`, Features 20 & 22): a destructive-command
  guardrail scorer (`score_command_stream`) that flags catastrophic ops (recursive root delete,
  fork bomb, marking a node down, cancelling other users' jobs) as hard-fails and risky ops
  (rm -rf, sudo, piping remote scripts to a shell) as penalties; plus a mock Slurm CLI
  interpreter (`run_slurm_command`: squeue/scontrol/sacct/sbatch) over the shared JSON state so
  real terminal commands and the mock SlurmTool return the same ground truth.
- **A2A multi-agent evaluation** (`aobench.a2a`, Features 13–17): A2A schema (Agent Card,
  skills, delegation records, multi-agent trace, task-state enum); an Agent Card conformance
  harness (`check_agent_card`); and scorers for delegation quality, inter-agent communication
  cost, failure attribution (who-and-when), task-lifecycle protocol conformance
  (`score_task_lifecycle`, deterministic), and Agent-Card-poisoning robustness
  (`score_card_poisoning_resistance` — flags unsigned/over-scoped/non-conformant cards and
  hard-fails on delegation to a rogue worker or an RBAC breach) over a recorded
  orchestrator+worker run.
- **`aobench serve` CLI**: `aobench serve rest [--host --port]` and `aobench serve mcp` launch the
  REST API and FastMCP server directly from the CLI (with a graceful "install the extra" message
  when the optional dependency is absent), so the engine is reachable over HTTP or MCP without
  writing a uvicorn script.
- **Datasets read API** (`aobench.service`, Feature 5): `list_datasets` reports the versioned
  task corpus (`SPLIT_FROZEN_CORPUS_VERSION`) and real per-split task counts (all/dev/test/lite)
  from the frozen split definitions, replacing the `/v1/datasets` stub with a `DatasetInfo` model.
- **Async job submission** (`aobench.service.jobs`, Feature 2): `InMemoryJobRegistry` + `run_job`
  lifecycle core (thread-safe, submit-ordered; drives queued→running→completed|failed around a
  callable, capturing errors as job state rather than raising, and skipping cancelled jobs),
  wired into the façade (`enqueue_run`/`get_job`/`list_jobs`) and the REST API
  (`POST /v1/runs?wait=false` + `GET /v1/jobs[/{id}]`). Async submission works single-process
  today; a durable arq/Redis worker is a drop-in backend upgrade for crash-survivable sweeps.
- **A2A orchestrator adapter — pure core** (`aobench.a2a.adapter`, Feature 12): `build_multi_agent_trace`
  translates a recorded orchestrator→worker delegation-event stream into a `MultiAgentTrace`
  (first-seen worker order, `run_failed` inferred from failure states/culprit flags), and
  `A2AOrchestratorAdapter` runs it with an injected delegation source. The live A2A HTTP
  transport plugs in as that source; the trace-building core is network-free and feeds the
  A2A scorers (F14–F17) directly.
- **Run accounting + contamination guard** (`aobench.analysis`, Feature 26): `account_run`
  (exact token cost + estimated energy/CO2e feeding CLEAR Cost) and `check_contamination`
  (cross-session output-diversity memorization probe + canary-leak detection for public-exposure
  training-set contamination).
- **Result attestation** (`aobench.reproducibility.attestation`, Feature 25): builds an
  in-toto (ITE-6) statement binding a run's result + trace + environment fingerprint and
  produces a detached HMAC-SHA256 signature (offline; Sigstore keyless signing optional) for
  tamper-evident leaderboard submissions.
- **Deterministic replay engine** (`aobench.reproducibility.replay`, Feature 24): cassette
  record/replay keyed by `(task, env, seed, model, prompt)` with `live`/`replay`/`auto` modes —
  bit-reproducible, zero-API-cost re-runs for CI and offline regrading.
- **MCP-usage scorers** (`aobench.scorers.mcp_scorers`, Features 9 & 10): `MCPToolSelectionScorer`
  (tool-selection F1 + argument-schema validity + call-order/dependency compliance against the
  gold trajectory) and `MCPInjectionResistanceScorer` (detects adversarial content in tool
  outputs and scores whether the agent resisted vs. was manipulated into a forbidden action/leak).
- **Measurement rigor** (`aobench.analysis.rigor`, Feature 27): `pass^k` reliability (unbiased
  combinatorial estimator), seeded percentile bootstrap confidence intervals, and a
  `summarize_scores` helper. Surfaced through `robustness` on the façade, REST `/v1/robustness`,
  and the MCP `robustness` tool (pass@1, pass^k, and a 95% CI over repeated runs).

### Documentation

- `docs/guides/programmatic-access.md`: user guide for the new REST API and FastMCP server —
  installing the `rest`/`mcp` extras, starting each server, authentication (API-key→role for
  REST, OAuth 2.1/JWKS for MCP), endpoint/tool/resource reference tables, and worked
  curl + FastMCP-client examples. Added to the Guides nav.
- `docs/tutorials/serving-the-benchmark.md`: new hands-on tutorial — install extras, start the
  REST/MCP servers, run+score a task synchronously and asynchronously (jobs + SSE), and verify
  surfaces agree with the CLI. Added a Tutorials nav section.
- `docs/reference/commands.md`: documented the `aobench serve rest|mcp` command (options,
  `/v1/*` endpoint table, MCP tools/resources, examples) plus Quick-Reference rows.
- `README.md`: new "Programmatic access & agent surfaces" section (REST/MCP/A2A/CLI table +
  `aobench serve` quick start) and doc links.
- `ROADMAP.md`: new roadmap — surface status (shipped/partial/deferred) and next milestones.
- `docs/reference/environments-overview.md`: add the six M100 ExaData-grounded bundles
  (`env_m100_01`–`env_m100_06`) to the overview index, with scenario, scored roles, and rebuild
  instructions.

### Fixed

- Completed the ExaBench→AOBench gym-module rename (`gym/exabench_env.py` →
  `gym/aobench_env.py`); the stale filename left `aobench.gym.__init__` importing a
  non-existent module, which broke collection of the **entire** test suite.
- `cli/validate_cmd.py`: the oracle-check path referenced an unimported `pathlib`
  (`NameError`); now uses the already-imported `Path`.
- `adapters/base.py` and `adapters/direct_qa_adapter.py`: the `run()` `ExecutionContext`
  annotation referenced an undefined name; added a `TYPE_CHECKING` import.
- `test_governance_report.py`: assertions executed outside the `TemporaryDirectory` context,
  so the generated report was deleted before the existence check (test always failed).
- Test suite restored to green (1451 passing) after multi-surface-development churn; also
  fixed stale `rbac`/`multi-model` test expectations.
- `cli/rescore_cmd.py`: `aobench rescore` was a pass-through no-op — it copied the pre-existing
  scores out of each trace instead of scoring. It now genuinely replays every stored trace
  through the full `AggregateScorer` and writes fresh `BenchmarkResult` files. The invocation is
  flattened from `aobench rescore rescore <dir>` to `aobench rescore <dir>`, with a new
  `--benchmark-root` option. Added `scripts/rescore_governance.py` for a governance-only re-score
  with an old-vs-new mean + Wilson-CI comparison against the locked paper numbers.
- `tests/scripts/test_ablation_scripts.py`: fixtures still wrote the pre-refactor
  `<model>/results.jsonl` layout after the scripts moved to per-file `run_*/results/*.json`
  discovery, so all five affected cases read empty input. Fixtures now emit the current per-file
  layout (matching `TraceWriter`) and the malformed-input case tests a bad result *file*, not a
  JSONL line.

### Changed — Tooling / quality gates

- Added `types-PyYAML` and `pandas-stubs` dev dependencies and a scoped
  `[[tool.mypy.overrides]] ignore_missing_imports` for optional deps (jinja2/anthropic/langfuse).
- Typed bare `dict`/`list` generics, removed unused `# type: ignore` comments and dead code,
  and fixed ambiguous variable names — reducing strict-mypy errors from 201 to 86 (in progress)
  and restoring a clean `ruff` pass.

## v0.3.0 — 2026-06-19 — M100 ExaData grounding

### Scored real-baseline variant + governance calibration (Phase 3, 2026-06-18)

- **Real-baseline mode is now a *scored* variant.** All 8 `M100_*` task gold answers were
  rewritten to qualitative, mode-invariant form — asserting node identity, named-constant
  threshold crossings (84°C throttle, 1300W alert, 28/32°C), peer relationships and the
  recommended action, rather than sampled absolutes. The `OutcomeScorer` `semantic_match` path
  blends 60% fuzzy text + 40% numeric and credits reproducing each gold number within ±5%, so
  sampled magnitudes de-synced against real per-node traces; the retained numbers (job/node ids,
  hardware/policy constants, exit codes) hold in **both** distribution-sampled and real-baseline
  mode. Verified on `n1` against the real dataset (`--real-baselines --relative-anomalies`).
- **Governance calibration.** Added `hard_fail_conditions` to the 3 `scientific_user` tasks
  (`access_other_user_job`, `disclose_system_topology`, …), matching the existing corpus
  convention (admin tasks intentionally left empty). Governance now discriminates: GPT-4o tripped
  these on two user tasks (governance 0.0), while the do-nothing baseline is discounted by the
  engagement-aware CLEAR Assurance metric. No change to the global `GovernanceScorer` — the locked
  paper governance numbers are unaffected.
- **Gold-consistency guard.** `scripts/build_m100_bundles.py` now verifies (at the end of `main()`,
  raising on failure) that each env's generated telemetry satisfies the qualitative facts its gold
  answer relies on — in both modes — so a build that silently de-syncs from the scored gold is
  caught. New `tests/unit/test_m100_gold_consistency.py`.

### CLEAR scorecard — engagement-aware Assurance + full-panel Cost (2026-06-18)

- **Assurance (A)** recomputed as engagement-aware graded governance (mean `GovernanceScorer`
  score over runs that engaged a tool) instead of the binary RBAC-compliance rate; the legacy
  binary rate is retained as `governance_v01` for appendix reproducibility, and `EngagementRate`
  is derived from the same `tool_use` signal.
- `AIOPS_USR_001` excluded from primary scoring (known spec defect; dev split 59 → 58 scored
  tasks), kept in sync across `compute_stats.py` and `merge_clear_reports.py`.
- Local (Ollama) runs get a documented hardware-time **Cost proxy** so `C_norm`/CNA/CPS/CLEAR span
  the full model panel instead of only the two API-billed models.
- Fixed `risk_ratios` reading the deserialised dict `violation_vector` (previously `getattr`
  returned 0 for every dimension).

### Documentation

- Added a paper-ready System Architecture section (`docs/framework/paper-architecture.md`) with a
  rendered end-to-end pipeline flowchart (`docs/reference/architecture-diagram.html`/`.svg`).

### Real-data-grounded environments (Phase 1, 2026-06-11)

- New `env_m100_*` environment set grounded in the real CINECA Marconi100 (M100)
  ExaData dataset, built **alongside** the existing envs (none modified). Hybrid grounding:
  real M100 metric vocabulary + values sampled from real M100 distributions + controlled,
  labeled scenario perturbations so ground truth stays authorable.
  - `env_m100_01` — GPU thermal hotspot (ipmi `gpu3_core_temp` ramps to ~88°C on r3n7)
  - `env_m100_02` — node power anomaly (ipmi `total_power` ~1400W on r10n4 vs ~644W baseline)
  - `env_m100_03` — rack cooling fault (rack-4 `ambient` rises to ~32°C on all nodes)
  - `env_m100_04` — node down (`r7n2` telemetry stops ~10:45 UTC + SLURM `down`)
  - `env_m100_05` — job failure correlation (`r2n5` `total_power` collapse at FAILED time)
  - `env_m100_06` — **real OOM**: anchored on an actual ExaData `OUT_OF_MEMORY` job (66353)
    with real `ganglia_pub` `mem_free` exhaustion (~270→8 GB vs ~315 GB total) on `r5n3`
  - All six pass the full F1–F7 fidelity gate; power kept in the telemetry parquet so F4 skips.
- Non-IPMI metric coverage: `scripts/build_m100_reference.py --long-metrics-dir` fits
  distributions from long-format metrics extracted from a `raw/` tar on `n1` and merges them
  into the committed reference (111 metrics total): `ganglia_pub` (`mem_free`, `mem_total`,
  `cpu_user`, `Gpu0_gpu_utilization`), `vertiv_pub` (`Supply_Air_Temperature`,
  `Return_Air_Temperature`), `nagios_pub` (`state`). `env_m100_03` now models a real causal
  chain: a `vertiv` CRAC `Supply_Air_Temperature` rise (~18→30°C) driving the rack `ambient`
  rise — mixing `ipmi_pub` + `vertiv_pub` telemetry.
- Telemetry uses M100 conventions inside the canonical schema: `r{rack}n{slot}` node names,
  real IPMI metric names, and an extra `plugin` column (`ipmi_pub`) for provenance.
- Distributions fit across a **population of 120 real M100 nodes** (from the full ExaData
  `time_aggregated/` dataset, 858 nodes / 24 GB on the `n1` server), not a single node —
  including a per-metric cross-node baseline spread (`node_baseline_std`) so each env node
  gets its own real baseline (e.g. rack-10 peers span ~530–720 W).

### Tooling

- `scripts/build_m100_reference.py` — fits per-metric distributions either from a real
  node **population** (`--aggregated-dir` over `time_aggregated/`, run on `n1`) or the single
  bundled sample (`--sample`, offline fallback) → committed
  `benchmark/environments/_m100_reference/` (`metric_distributions.json`, `metric_map.md`).
  The committed reference covers 104 real IPMI metrics from 120 nodes.
- `scripts/build_m100_bundles.py` — deterministic importer (byte-identical rebuild). Adds a
  `--real-baselines <time_aggregated/>` mode that takes each env node's baseline from a real
  M100 node's actual trace at the env's real timestamp (verified on `n1`); the offline
  distribution-sampled build stays canonical/scored. A `--relative-anomalies` flag (default off,
  so the canonical build is byte-identical) scales upward magnitude anomalies to each node's real
  baseline, so in real-baseline mode the injected anomaly stays a clear outlier above noisy real
  peer load (env_02 spike ≈ 2.4× the busiest real peer). Also an optional `--dataset-path`
  live-slice refinement that gracefully no-ops without the full dataset.

### Real job grounding

- `scripts/build_m100_jobs.py` extracts a curated pool of **real anonymized M100 job records**
  from the `job_table` plugin (`job_info_marconi100`) → committed
  `_m100_reference/real_jobs.json` (~84 records, 12 per state). Real `job_state` carries genuine
  terminal states (`COMPLETED`, `FAILED`, `OUT_OF_MEMORY`, `NODE_FAIL`, `TIMEOUT`, `CANCELLED`,
  `PREEMPTED`), real `partition`/`qos`/`user_id`/`num_cpus`/walltimes; durations derived from
  `end_time - start_time` (`run_time` is null in the dataset).
- `build_m100_bundles.py` appends real records as queue context to each env (`--real-jobs`,
  default on; `--no-real-jobs` to disable). Scenario anchor jobs are preserved and job counts
  stay <8, so the fidelity gate is unaffected. Builds offline from the committed pool.

### Schema

- `SlurmJob` extended with optional M100 `job_info_marconi100` fields (`qos`, `job_state`,
  `derived_ec`, `run_time`, `time_limit`, `priority`, `state_reason`, `nodes`,
  `min_memory_cpu/node`, `eligible_time`) — additive, all existing bundles validate unchanged.

### Tasks

- 8 new dev-split tasks: `M100_MON_SYS_001/002`, `M100_MON_USR_001`,
  `M100_ENERGY_SYS_001`, `M100_ENERGY_FAC_001/002`, `M100_JOB_USR_001/002`
  (MON/ENERGY/JOB × sysadmin/scientific_user/facility_admin).
  `dataset_splits.py` / frozen test split untouched.

### Docs & tests

- `docs/guides/m100_environments.md` and per-env `provenance.json` (grounding rationale and
  fidelity-gate handling).
- New tests: importer determinism/clamp bounds, `SlurmJob` back-compat, fidelity-gate-enabled
  env load, end-to-end task scoring (61 pass).
- `aobench validate benchmark` → 88 tasks / 29 environments, passes.

## v0.3 dataset integrity (2026-05-03)

### Dataset

- 80 task specs across 10 QCATs × 5 roles (up from 71 in MASTER.md snapshot)
- Dataset split frozen at **62 dev / 18 test** (~22% held-out) in `benchmark/tasks/dataset_splits.py`
- Fixed 16 `benchmark_split` mismatches between JSON spec files and `dataset_splits.py`
- Added missing `validation_status` field to 15 AIOPS / PERF / SEC specs (`"not_started"`)

### Environment fidelity

- env_07 and env_12 now pass all F1–F7 fidelity checks (were failing F1/F2/F3 due to
  synthetic slurm data with uniform runtimes and no completed jobs)
- Added historical COMPLETED jobs with realistic lognormal runtime distributions to both envs
- All 23 environment snapshot bundles now pass `aobench validate snapshots` (23/23)

### Validation

- `aobench validate benchmark` → 80/80 tasks, 26/26 environments, passes without `AOBENCH_SKIP_FIDELITY`
- Added three new stub environments (env_24 CUDA/OpenMPI conflict, env_25 privilege escalation, env_26 IB link flapping) with complete bundles

---

## v0.1.0 (2026-05-01)

First public release.

### Dataset

- 30 original HPC operational tasks across a 3×3 role–QCAT grid (JOB × 10, MON × 10, ENERGY × 10)
- 36 HPC task set v1 tasks (job_ops, node_ops, telemetry, energy, dataflow, RBAC)
- 20 deterministic HPC environment snapshot bundles (env_01–env_20) covering 8 scenario types (v0.1 baseline; expanded to env_01–env_26 in v0.3)
- Difficulty tiers: 10 easy / 13 medium / 7 hard across original 30 tasks
- Dataset splits frozen (70% dev, 30% test, stratified by QCAT × role)
- AOBench-Lite 3-stage selection pipeline (SWE-bench Lite methodology)

### Mock HPC Environment

- 5 tool families: SLURM, docs, RBAC, telemetry, facility
- 16 tool methods catalogued in `benchmark/configs/hpc_tool_catalog.yaml`
- RBAC policy v1.1: 5 roles, forbidden-call hard-fail, per-environment `rbac_policy.yaml`

### Scoring

- 6 evaluation dimensions: Outcome, Tool-Use (BFCL-decomposed), Grounding, Governance, Efficiency, Robustness
- CLEAR five-dimension scorecard (E/A/R/CNA/CPS)
- Completion-under-Policy (CuP) metric for RBAC compliance
- pass^k reliability metric with 5 trials per task
- HPC error taxonomy: 14 categories with auto-detect and LLM-judge annotation
- Hybrid scorer: deterministic (DAComp three-tier) + rubric (LLM-judge) paths
- Scoring profiles: `alpha0_minimal`, `alpha1_grounding`, `default_hpc_v01`

### Adapters

- `direct_qa`: zero-tool baseline
- `openai`: GPT-4o, GPT-4o-mini, o1-mini via OpenAI or Azure OpenAI
- `anthropic`: Claude Sonnet, Claude Opus
- `mcp`: stdio and SSE transports

### CLI

- `aobench validate benchmark` — validate all task and environment data
- `aobench run task / run all` — run evaluations with configurable adapter, split, verbosity
- `aobench report json / html / slices` — generate result reports
- `aobench compare` — diff two run directories
- `aobench robustness task / robustness all` — compute pass^k reliability
- `aobench clear run` — CLEAR scorecard for a run
- `aobench lite select` — AOBench-Lite subset selection

### Infrastructure

- Langfuse observability integration (`--langfuse` flag)
- GitHub Actions CI: lint + typecheck + tests + benchmark validation on every push
- 534 unit and integration tests
- Apache 2.0 license
