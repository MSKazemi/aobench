# Authors and contributors

AOBench is built by the people below. **Every merged contribution earns a line here,
whatever its size** — a typo fix in the docs is a real contribution to a project whose
docs are the product. So does a bug report that turns out to be right; those are listed
under [Reported and tested](#reported-and-tested).

## Maintainers

- **Mohsen Seyedkazemi Ardebili** ([@MSKazemi](https://github.com/MSKazemi)) —
  ORCID [0000-0002-1166-6559](https://orcid.org/0000-0002-1166-6559) —
  University of Bologna (DEI)
- **Andrea Bartolini** —
  ORCID [0000-0002-1148-2450](https://orcid.org/0000-0002-1148-2450) —
  University of Bologna (DEI)

## Contributors

Added when a first PR merges, newest last.

- **abhinav** ([@erensh27](https://github.com/erensh27)) — AOBench's first external
  contributor. Took [issue #2](https://github.com/MSKazemi/aobench/issues/2) and replaced
  the raw traceback on a mistyped `--task` / `--env` with an actionable one-line error,
  with end-to-end CLI tests
  ([PR #25](https://github.com/MSKazemi/aobench/pull/25)). Those tests then caught a
  ranking bug in the maintainer's own overlapping implementation, which is why
  `aobench run task --task JOB_USR_00` suggests `JOB_USR_001` today.

- **Barshana Chatterjee** ([@Barshana24](https://github.com/Barshana24)) — took
  [issue #29](https://github.com/MSKazemi/aobench/issues/29) and gave `report json` and
  `compare runs` a `--json` flag, so AOBench can be wired into CI without scraping
  formatted tables ([PR #43](https://github.com/MSKazemi/aobench/pull/43)). Also spotted
  that the issue named a `report summary` command that does not exist, and said so
  instead of inventing one. Came back for
  [issue #28](https://github.com/MSKazemi/aobench/issues/28) and built
  `aobench list coverage`, which turns "where is this benchmark thin?" from a shell
  pipeline over filenames into one command
  ([PR #47](https://github.com/MSKazemi/aobench/pull/47)) — and, told not to parse
  filenames, worked out for herself *why*: the `M100_` tasks carry an extra ID segment
  that shifts every position after it. The design call on how to count those tasks was
  hers, made and defended before anyone asked. Came back a third time for
  [issue #37](https://github.com/MSKazemi/aobench/issues/37) and cleared `mypy --strict`
  across the whole of `cli/` ([PR #50](https://github.com/MSKazemi/aobench/pull/50)) —
  and did it by *narrowing* the types rather than silencing them, which is the harder
  and more useful half. The `validate_cmd` fix in it is a small piece of real reading:
  one function reused the name `overall` for two different types across two loops, and
  mypy pins a name to its first assignment for the whole function. She also found a
  latent `None`-comparison crash in `robustness_cmd` while in there, and filed it as
  [#49](https://github.com/MSKazemi/aobench/issues/49) instead of quietly widening the
  PR — the scope discipline that makes a typing PR reviewable at all.

- **Leo Zhao** ([@LobsterQBA](https://github.com/LobsterQBA)) — took
  [issue #31](https://github.com/MSKazemi/aobench/issues/31) and wrote
  `examples/05_compare_two_adapters.py`, the side-by-side comparison the benchmark exists
  for and the one thing the first four examples never showed
  ([PR #44](https://github.com/MSKazemi/aobench/pull/44)). It reuses `aobench compare runs`
  rather than re-deriving the deltas, and registers itself in the example smoke tests, so
  the README's promise that a broken example breaks the build stays true. Came back for
  [issue #3](https://github.com/MSKazemi/aobench/issues/3) and taught `aobench report` to
  say what went wrong when a run directory is missing or empty — naming the path, listing
  the runs that *do* exist, and separating "you typed the wrong path" from "the run
  produced nothing" ([PR #48](https://github.com/MSKazemi/aobench/pull/48)). He also
  disclosed his use of AI assistance unprompted and reported exactly which gates he had
  and had not been able to run, which is the part that made the review cheap.

- **Atiqur Rahman** ([@atiqur-rahman-pro](https://github.com/atiqur-rahman-pro)) — noticed
  that `scripts/` was the one Python directory sitting outside every quality gate, and did
  the unglamorous read across 31 of its files
  ([PR #45](https://github.com/MSKazemi/aobench/pull/45)). Those 55 scripts generate the
  docs catalogs, the RBAC policy pages and the frozen paper tables, so `ruff check` now
  covers them in CI. Narrowing their blanket `except Exception` handlers also exposed a
  latent crash in the tool-docs generator that an empty `metadata.yaml` had been able to
  abort since the script was written. Then split a second finding out of that PR rather
  than burying it in it: the rubric reliability gate computed `ICC1` while its docstring,
  its error message, the docs and its own test module all said `ICC(A,1)` — two different
  statistics under one name ([PR #46](https://github.com/MSKazemi/aobench/pull/46)). The
  gate is dormant until multi-judge scoring is switched on, which makes this the cheapest
  moment it could possibly have been caught.

- **Dream** ([@TrueFurina](https://github.com/TrueFurina)) — wrote
  [Your first 10 minutes with AOBench](https://mskazemi.com/aobench/latest/getting-started/first-10-minutes/),
  the one page the documentation did not have
  ([PR #52](https://github.com/MSKazemi/aobench/pull/52)). Everything a newcomer needed
  existed already, spread across five pages; the contribution was noticing that the
  *route* through them was the missing artifact, and writing a single unbranched path
  from `git clone` to reading a score. That is a documentation judgement, not a
  documentation chore.

- **lorenzo-benites** ([@lorenzo-benites](https://github.com/lorenzo-benites)) — took the
  `mypy --strict` paydown across three packages in three PRs: `reports/`
  ([PR #53](https://github.com/MSKazemi/aobench/pull/53)), `leaderboard/`
  ([PR #54](https://github.com/MSKazemi/aobench/pull/54)) and `judge/`
  ([PR #55](https://github.com/MSKazemi/aobench/pull/55)), closing
  [issues #38 and #39](https://github.com/MSKazemi/aobench/issues/38). Two of those
  carried real correctness work rather than annotations: `_parse_json_response` in the
  judge now verifies that a parsed payload is actually an object before returning it as
  one — a judge reply of `[1, 2]` or `"ok"` used to sail through as a dict — and the
  Anthropic branch now checks the content block's type instead of assuming the first
  block has `.text`. Reported honestly, and usefully, that he develops on Windows and so
  could not run `make check`, naming exactly which checks he had run instead. Came back
  for [issue #58](https://github.com/MSKazemi/aobench/issues/58) and cleared `scorers/`
  ([PR #59](https://github.com/MSKazemi/aobench/pull/59)) — 26 errors to 1, the last one
  deliberately out of scope. That one included the reachable half of the Anthropic
  content-block bug: `rubric_scorer` assumed the first block carried `.text`, which is
  false whenever extended thinking is on. He also worked out on his own that the broad
  `float | None` on `raw_outcome` was the cause rather than a symptom, and said so
  instead of widening the annotation.

- **[@Akimbo92i](https://github.com/Akimbo92i)** — closed out the `mypy --strict` epic.
  Took [issue #61](https://github.com/MSKazemi/aobench/issues/61) and cleared the last ten
  errors, in the five mock HPC tools that every task in the benchmark runs through
  ([PR #64](https://github.com/MSKazemi/aobench/pull/64)). `mypy_baseline.json` went from
  11 errors to 1, and `tools` now carries **no budget at all** — a package with no recorded
  budget must report zero, so the ratchet stops it rotting back. He also answered the
  question the issue asked rather than only the one in its title. Told that `facility_tool`
  alone reports a different error because its four handlers genuinely do not share a
  signature, he argued that the heterogeneity *is* the contract — the tool boundary takes
  dynamic keyword arguments, and the invariant worth enforcing there is the shared
  `ToolResult` return — and annotated to that instead of forcing the layer into a uniform
  shape it does not have. And he reported, unprompted, that `pytest tests/unit -k tool`
  failed on a test his change never touched, together with the observation that it passed
  alone and in a full run. It does that on `main` too: a fixture in
  `test_langfuse_exporter.py` imports the module *inside* `patch.dict(sys.modules, ...)`,
  so exiting the block evicts it again and the next `importlib.reload` raises. A
  five-month-old test-isolation bug, found by running a gate nobody had asked him to run
  and saying so instead of quietly re-running until it went green — filed as
  [#65](https://github.com/MSKazemi/aobench/issues/65).

- **Enzo** ([@motodriver](https://github.com/motodriver)) — closed
  [issue #65](https://github.com/MSKazemi/aobench/issues/65), the test-isolation bug found
  by [@Akimbo92i](https://github.com/Akimbo92i) above
  ([PR #67](https://github.com/MSKazemi/aobench/pull/67)). `patch.dict(sys.modules, ...)`
  restores the snapshot it took on entry, so a module first imported *inside* the block gets
  evicted again on exit; a later `importlib.reload` on the still-live module object then
  raises. The fix is one idea applied at all six call sites in
  `test_langfuse_exporter.py`: import the module once at module scope, before any
  `patch.dict` block opens, so the snapshot already contains it and restoring is a no-op.
  Disclosed substantial AI assistance (TRAE) in the PR description, as `CONTRIBUTING.md`
  asks.

- **Qiu Guanzong** ([@QIU-Guanzong](https://github.com/QIU-Guanzong)) — closed
  [issue #66](https://github.com/MSKazemi/aobench/issues/66):
  `MockSlurmTool._load_json` was annotated `-> dict[str, Any]`, but three of the seven
  `job_details.json` corpus snapshots are top-level lists, and `_job_details_method` already
  branched on `isinstance(..., list)` to handle both — the annotation was a claim mypy
  accepted without checking ([PR #68](https://github.com/MSKazemi/aobench/pull/68)). A
  single widened return type would not have worked on its own, since `_query_jobs` calls
  `self._state.get("jobs", [])` and `list` has no `.get`. The fix is a `@overload` pair: a
  `Literal["slurm/slurm_state.json"]` overload keeps the state-snapshot path typed as a
  mapping, and the general path returns the true `dict | list` union that `job_details`
  actually has — runtime unchanged by construction. Added parametrized regression tests
  pinning both snapshot shapes across the whole corpus. Disclosed AI assistance (Codex) in
  the PR description.

## Reported and tested

Not every contribution is a commit. The people below ran AOBench somewhere the maintainer
could not and reported what broke; each was correct on the first telling, and each report
is now a fix on `main`.

- **hari760** ([@hari760](https://github.com/hari760)) — submitted a three-run
  `claude-sonnet-4-6` result on the dev split
  ([#60](https://github.com/MSKazemi/aobench/issues/60)) and, in the process of filling in
  the form honestly, found four defects. The headline one: a first run died at task 6 of
  67 with a `UnicodeEncodeError`, and the diagnosis came attached and correct — text I/O
  with no explicit `encoding=` falls back to the platform preferred encoding, which is
  cp1252 on Windows, and model output contained an emoji. It was not one call site but
  **259**, across `src/`, `tests/` and `scripts/`; the read path was equally exposed and
  had simply not been reached, since the corpus itself contains em-dashes. Linux CI cannot
  see this class of bug at all, so it is now a static gate (`make encoding-check`). The
  other three came from the fields left blank rather than guessed: the missing
  per-dimension breakdown exposed that `workflow` — 0.10 weight in `default_hpc_v01` — was
  absent from every task row, from the OTel export and from `compare runs --show-dims`, so
  the breakdown could never have reconciled against the aggregate it explained; the
  scoring-profile field asked for one profile where the corpus sets it per task, 60
  `alpha1_grounding` to 28 `default_hpc_v01`, which was worked out unaided and reported
  precisely; and the documented submission command redirected a command that prints prose,
  not JSON. Four defects from one submission, right about all of them.

- **userfypp** ([@userfypp](https://github.com/userfypp)) — took the DOCS_USR cell on
  [#26](https://github.com/MSKazemi/aobench/issues/26), checked the proposed task against
  `env_21` **before** writing the spec, and stopped when the gold answer turned out to be
  unreachable. `MockDocsTool._retrieve` matched on a document's full text and then returned
  `content[:500]` as the snippet, so the match succeeded and the evidence was discarded —
  the tool reported a hit whose snippet contained none of the query terms. The consequence
  is worse than truncation: an agent could be scored on grounding against evidence the tool
  would never surface, silently capping the grounding dimension on any task whose answer
  lives late in a long document, under a comment that read as though it were intentional.
  Snippets are now windows centred on the most selective matched term, with regression
  tests in `tests/unit/test_docs_tool_snippet.py` built from the exact queries reported.

## Design and interoperability

- **Sahi** ([@adhabnr-ux](https://github.com/adhabnr-ux)) — proposed an
  [EvalPort](https://github.com/adhabnr-ux/evalport) eval-interchange adapter in
  [discussion #51](https://github.com/MSKazemi/aobench/discussions/51), with a complete
  field-by-field mapping of `TaskSpec` / `Trace` / `BenchmarkResult` onto the schema and a
  working code sketch. The mapping was derived from reading `src/aobench/schemas/` rather
  than the README, and is correct in the places that are easy to get wrong — including
  routing `dimension_scores` to one grader result per dimension and carrying
  `weight_profile_name` through to the result metadata. The contribution that matters,
  though, is the part that did **not** map: an RBAC hard fail zeroes an entire task
  including the dimensions the agent handled well, and a per-dimension grader slot cannot
  express a statement about the validity of the whole row. That was raised as an open
  question about how interchange formats should model hard constraints in general, before
  any code was written, rather than resolved silently in one direction. It is a real gap in
  the field and not merely in one adapter.

## Work in flight

Recorded so effort is not duplicated, and because a claim deserves acknowledging before it
lands rather than only after. **Claiming an issue protects it** — nothing gets merged over
a claim.

- **[@hoti-code](https://github.com/hoti-code)** — building the
  [LiteLLM adapter](https://github.com/MSKazemi/aobench/issues/33) (one file, ~100
  providers), claimed 2026-09-01. Asked whether `litellm:<model>` with the provider prefix
  passed through was the intended adapter-string format *before* writing code, which is
  why it will not need redoing in review.
- **[@userfypp](https://github.com/userfypp)** — writing a second DOCS_USR task on the PII
  storage policy ([#26](https://github.com/MSKazemi/aobench/issues/26)), claimed
  2026-08-11, unblocked once the docs-retrieval bug they found was fixed.
- **[@aawhan0](https://github.com/aawhan0)** — verifying that the 136 documented shell
  commands actually do what their pages claim, from a clean checkout, starting with
  `docs/getting-started/quickstart.md` ([#62](https://github.com/MSKazemi/aobench/issues/62)),
  claimed 2026-09-10. They volunteered for precisely this work on
  [#32](https://github.com/MSKazemi/aobench/issues/32) on 2026-08-27 and the claim was
  never acknowledged before a parallel PR closed the issue — see the
  [apology](https://github.com/MSKazemi/aobench/issues/32#issuecomment-5609993851). The
  claims table on [#20](https://github.com/MSKazemi/aobench/issues/20) exists because of
  that failure.
- **[@BillP313](https://github.com/BillP313)** — recording a 30-second demo GIF for the
  README ([#9](https://github.com/MSKazemi/aobench/issues/9)), claimed 2026-09-11.

<!-- Add yourself in your first PR: - **Your Name** (@handle) — what you contributed -->

## Acknowledgements

- **CINECA** for publishing the Marconi100 **ExaData** release, which is what lets six
  of AOBench's environments be grounded in real Tier-0 operational data rather than
  invented. A benchmark of this kind is only as credible as the real data underneath
  it.
- The authors of **BFCL**, **τ-bench**, **SWE-bench**, and **TRAIL**, whose evaluation
  designs AOBench borrows from directly and cites in
  [related work](https://mskazemi.com/aobench/latest/about/related-work/).

## Recognition policy

- **Code, docs, tests, corpus, review, and bug reports** all count. Reviewing someone
  else's PR carefully is a contribution, and so is a report that turns out to be right —
  both get listed.
- **Release notes name contributors** for the version their change shipped in.
- **Substantial corpus or methodological contributions may warrant co-authorship** on a
  paper that depends on them. If you believe that applies to your work, say so — the
  awkwardness of asking should not decide who gets credit.
- **Contributions stay listed** even if you later step away.

To add yourself, edit this file in the same PR as your change. If you would rather not
be listed, that is fine too — just say so in the PR.
