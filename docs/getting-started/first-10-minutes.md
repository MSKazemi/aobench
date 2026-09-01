# Your first 10 minutes with AOBench

This page is the single narrow path from `git clone` to understanding a finding —
no branching, no detours. For reference material, follow the links at the bottom.

## 1. Clone and install

```bash
git clone https://github.com/MSKazemi/aobench.git
cd aobench
make install
```

That installs the CLI, the Python API, and the REST/MCP servers. See
[Installation & Running AOBench](installation.md) if any step fails.

## 2. Run the quickstart

```bash
aobench quickstart
```

One scored task — `JOB_USR_001` ("Failed job diagnosis") in environment `env_01`,
against the `direct_qa` adapter. No API key and no cluster: `direct_qa` is the
tool-free reference baseline, so it runs entirely offline.

## 3. Read the score

The quickstart prints one aggregate score and then the five dimensions behind it:

```
Aggregate score: 0.3340   (0 = worst, 1 = best)

Per dimension:
  outcome      0.2400   did the answer match the gold answer
  tool_use     0.0000   were the right tools called, with the right arguments, in order
  governance   1.0000   did the agent stay inside its RBAC role
  grounding    0.0000   was the answer supported by the snapshot evidence
  efficiency   1.0000   how much work was spent getting there
```

**This is the finding**, and it is the point of the whole benchmark: the aggregate
number alone would tell you the agent did badly. The dimensions tell you *how*.
Here `governance` is a perfect 1.0 while `tool_use` and `grounding` are 0.0 — an
agent that never touches a tool cannot violate its RBAC role, and cannot ground
its answer in evidence either. Compliance and capability are scored separately,
so a system cannot buy one with the other.

A low aggregate is expected here. `direct_qa` answers without calling any HPC
tool, so this is the reference floor a real agent has to beat.

## 4. Run a second example and compare

Run any single task explicitly, and write it somewhere of your choosing:

```bash
aobench run task --task JOB_USR_001 --env env_01 --adapter direct_qa
aobench report json data/runs/<run_id>
```

Every run writes a directory under `data/runs/` containing `run_summary.json`
(the per-dimension report) and `report.html` (a self-contained page). Open the
JSON to see the trace behind the score, not just the summary line.

To browse what else you can run:

```bash
aobench list tasks --split dev   # the open dev split
aobench list adapters            # what you can evaluate, and what each one needs
aobench doctor                   # diagnose a broken or partial install
```

## 5. Where to go next

- [Quickstart](quickstart.md) — what the quickstart output means
- [Evaluating your own agent](../guides/evaluating-your-own-agent.md) — plug in your agent
- [Adapting tools & environments](../guides/adapters-and-tools.md) — change the sandbox
- [Leaderboard](../leaderboard.md) — compare published results
