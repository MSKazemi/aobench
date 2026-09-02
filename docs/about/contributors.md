# Contributors

**Thank you.** AOBench is a benchmark, which means its value is not in the code — it is in
how carefully the 88 tasks, the 29 environments, the scoring rules, and the documentation
have been checked by people who were not the person who wrote them. Every fix, every
question that exposed an unclear page, every "this crashed for me" is that checking. This
page is where those people are named.

## Maintainer and advisor

<ul class="wall">
<li>
  <span class="wall-avatar">
    <img src="https://github.com/MSKazemi.png?size=144" alt="" loading="lazy">
    <span class="wall-badge" aria-hidden="true">🛠️</span>
  </span>
  <span class="wall-name">Mohsen Seyedkazemi Ardebili</span>
  <span class="wall-handle"><a href="https://github.com/MSKazemi">@MSKazemi</a></span>
  <span class="wall-role">Creator &amp; maintainer</span>
  <span class="wall-tag">Design, scoring, corpus, and the research behind them</span>
</li>
<li>
  <span class="wall-avatar">
    <span class="wall-initials" aria-hidden="true">AB</span>
    <span class="wall-badge" aria-hidden="true">🎓</span>
  </span>
  <span class="wall-name">Andrea Bartolini</span>
  <span class="wall-handle"><a href="https://orcid.org/0000-0002-1148-2450">ORCID</a></span>
  <span class="wall-role">Scientific advisor</span>
  <span class="wall-tag">Co-author</span>
</li>
</ul>

Authors for citation purposes are listed in [Cite AOBench](citation.md) and in
[`CITATION.cff`](https://github.com/MSKazemi/aobench/blob/main/CITATION.cff).

## Contributors

Listed in the order their first contribution merged. The badge on each avatar marks what
they worked on; the line underneath says it in words.

<ul class="wall">
<li>
  <span class="wall-avatar">
    <img src="https://github.com/erensh27.png?size=144" alt="" loading="lazy">
    <span class="wall-badge" aria-hidden="true">🧭</span>
  </span>
  <span class="wall-name">abhinav</span>
  <span class="wall-handle"><a href="https://github.com/erensh27">@erensh27</a></span>
  <span class="wall-role">First contributor</span>
  <span class="wall-tag">Friendly CLI errors</span>
</li>
<li>
  <span class="wall-avatar">
    <img src="https://github.com/Barshana24.png?size=144" alt="" loading="lazy">
    <span class="wall-badge" aria-hidden="true">🔌</span>
  </span>
  <span class="wall-name">Barshana Chatterjee</span>
  <span class="wall-handle"><a href="https://github.com/Barshana24">@Barshana24</a></span>
  <span class="wall-role">Contributor</span>
  <span class="wall-tag">Machine-readable output · coverage matrix · typed CLI</span>
</li>
<li>
  <span class="wall-avatar">
    <img src="https://github.com/LobsterQBA.png?size=144" alt="" loading="lazy">
    <span class="wall-badge" aria-hidden="true">⚖️</span>
  </span>
  <span class="wall-name">LeoZhaoo</span>
  <span class="wall-handle"><a href="https://github.com/LobsterQBA">@LobsterQBA</a></span>
  <span class="wall-role">Contributor</span>
  <span class="wall-tag">Side-by-side comparison · report error messages</span>
</li>
<li>
  <span class="wall-avatar">
    <img src="https://github.com/atiqur-rahman-pro.png?size=144" alt="" loading="lazy">
    <span class="wall-badge" aria-hidden="true">⚖️</span>
  </span>
  <span class="wall-name">Atiqur Rahman</span>
  <span class="wall-handle"><a href="https://github.com/atiqur-rahman-pro">@atiqur-rahman-pro</a></span>
  <span class="wall-role">Contributor</span>
  <span class="wall-tag">Lint gate for scripts/ · ICC(A,1) fix</span>
</li>
<li>
  <span class="wall-avatar">
    <img src="https://github.com/TrueFurina.png?size=144" alt="" loading="lazy">
    <span class="wall-badge" aria-hidden="true">📖</span>
  </span>
  <span class="wall-name">Dream</span>
  <span class="wall-handle"><a href="https://github.com/TrueFurina">@TrueFurina</a></span>
  <span class="wall-role">Contributor</span>
  <span class="wall-tag">The first-10-minutes path</span>
</li>
<li>
  <span class="wall-avatar">
    <img src="https://github.com/lorenzo-benites.png?size=144" alt="" loading="lazy">
    <span class="wall-badge" aria-hidden="true">🔎</span>
  </span>
  <span class="wall-name">lorenzo-benites</span>
  <span class="wall-handle"><a href="https://github.com/lorenzo-benites">@lorenzo-benites</a></span>
  <span class="wall-role">Contributor</span>
  <span class="wall-tag">Typed reports, leaderboard, judge &amp; scorers</span>
</li>
</ul>

| Contributor | What they added | |
|---|---|---|
| [@erensh27](https://github.com/erensh27) | An actionable one-line error, with tests, in place of the traceback you used to get from a mistyped `--task` or `--env` | [#25](https://github.com/MSKazemi/aobench/pull/25) |
| [@Barshana24](https://github.com/Barshana24) | `--json` on `report json` and `compare runs`, so AOBench's numbers can be piped into `jq` instead of scraped | [#43](https://github.com/MSKazemi/aobench/pull/43) |
| [@Barshana24](https://github.com/Barshana24) | `aobench list coverage` — the QCAT × role matrix, its thin and empty cells, and how much of each rests on real Marconi100 data | [#47](https://github.com/MSKazemi/aobench/pull/47) |
| [@LobsterQBA](https://github.com/LobsterQBA) | `examples/05_compare_two_adapters.py` — two systems side by side with per-dimension deltas, offline | [#44](https://github.com/MSKazemi/aobench/pull/44) |
| [@LobsterQBA](https://github.com/LobsterQBA) | `aobench report` now names a missing run directory and lists the runs that exist, instead of raising a traceback | [#48](https://github.com/MSKazemi/aobench/pull/48) |
| [@atiqur-rahman-pro](https://github.com/atiqur-rahman-pro) | `ruff check` over `scripts/` — the 55 generators behind the catalogs, RBAC pages and paper tables, previously outside every gate | [#45](https://github.com/MSKazemi/aobench/pull/45) |
| [@atiqur-rahman-pro](https://github.com/atiqur-rahman-pro) | The rubric reliability gate now computes `ICC(A,1)`, the statistic it had always documented, instead of `ICC1` | [#46](https://github.com/MSKazemi/aobench/pull/46) |
| [@Barshana24](https://github.com/Barshana24) | `mypy --strict` clean across `cli/` — narrowed, not silenced — plus a latent `None`-comparison crash found and filed rather than folded in | [#50](https://github.com/MSKazemi/aobench/pull/50) |
| [@TrueFurina](https://github.com/TrueFurina) | *Your first 10 minutes with AOBench* — one unbranched path from `git clone` to reading a score, the route the five existing pages never drew | [#52](https://github.com/MSKazemi/aobench/pull/52) |
| [@lorenzo-benites](https://github.com/lorenzo-benites) | `mypy --strict` clean across `reports/`, `leaderboard/` and `judge/`, and a judge that now rejects a non-object JSON reply instead of returning it as a dict | [#53](https://github.com/MSKazemi/aobench/pull/53), [#54](https://github.com/MSKazemi/aobench/pull/54), [#55](https://github.com/MSKazemi/aobench/pull/55) |
| [@lorenzo-benites](https://github.com/lorenzo-benites) | `scorers/` from 26 `mypy --strict` errors to 1, including the reachable Anthropic content-block bug in the rubric judge | [#59](https://github.com/MSKazemi/aobench/pull/59) |

This is a young project and that is a short list. It is worth reading anyway, because one
of those contributions has already paid for itself: the CLI tests in #25 failed
against the maintainer's *own* overlapping implementation and exposed a ranking bug in it —
`--task JOB_USR_00` was answering *"did you mean JOB_USR_005, JOB_USR_004, JOB_USR_003?"*
and silently omitting `JOB_USR_001`. A second person's test found what the author's own
tests were structurally unable to see. That is the argument for contributing here, and it
is the reason the list being short is a reason to add to it rather than a reason to wait.

## How you get on this wall

Every merged contribution earns a place here, whatever its size. A typo fix in the docs is
a real contribution to a project whose documentation *is* the product.

| If you want to… | Start here |
|---|---|
| Fix something small and well-specified | [Good first issues](https://github.com/MSKazemi/aobench/labels/good%20first%20issue) — each names the files, the tests, and an honest time estimate |
| Improve a page that confused you | Edit it directly; the pencil icon at the top of every page opens a PR |
| Report a bug or request a feature | [Open an issue](https://github.com/MSKazemi/aobench/issues/new/choose) |
| Propose a task or an environment | [Contributing guide](contributing.md) |
| Ask something | [Discussions](https://github.com/MSKazemi/aobench/discussions) — questions are welcome and expected |

You do not need HPC access or a cluster. The whole benchmark runs against frozen snapshots
on a laptop, and the `direct_qa` adapter needs no API key.

## What recognition means here

- **Code, docs, tests, corpus, and review all count.** Reviewing someone else's PR
  carefully is a contribution, and it gets listed.
- **Release notes name contributors** for the version their change shipped in, and the
  [changelog](changelog.md) links the person next to the fix.
- **Substantial corpus or methodological contributions may warrant co-authorship** on a
  paper that depends on them. If you think that applies to your work, say so — the
  awkwardness of asking should not be what decides who gets credit.
- **Contributions stay listed** even if you later step away.
- **You can decline.** If you would rather not appear here, say so in the PR and you won't.

## What you can expect from us

A first response within three working days, even when that response is only "seen, I'll
look properly on Friday". If a PR of yours goes quiet for longer, ping it — that is our
failure, not rudeness on your part.

We hold ourselves to that publicly because we have already missed it: PR #25 sat for a day
while an overlapping implementation was written and merged in parallel, which is the one
thing a maintainer most owes a contributor not to do. The [rework of that
PR](https://github.com/MSKazemi/aobench/pull/25) preserves the contributor's commits and
credit precisely because the mistake was ours.

## Acknowledgements

- **CINECA**, for publishing the Marconi100 **ExaData** release, which is what lets six of
  AOBench's environments be grounded in real Tier-0 operational data rather than invented.
  A benchmark of this kind is only as credible as the real data underneath it.
- The authors of **BFCL**, **τ-bench**, **SWE-bench**, and **TRAIL**, whose evaluation
  designs AOBench borrows from directly and cites in [related work](related-work.md).

---

The canonical, machine-readable record of everyone listed here is
[`AUTHORS.md`](https://github.com/MSKazemi/aobench/blob/main/AUTHORS.md) in the repository
root; this page is its presentation. Author metadata for citation purposes lives in
[`CITATION.cff`](https://github.com/MSKazemi/aobench/blob/main/CITATION.cff) — see
[Cite AOBench](citation.md).
