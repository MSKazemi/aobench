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
[Installation & Running AOBench](getting-started/installation.md) if any step fails.

## 2. Run the quickstart

```bash
aobench quickstart
```

This runs the default benchmark task against a default agent and prints a report to
the terminal. It is the fastest possible end-to-end run.

## 3. Look at the report

The report has three parts:

- **Task result** — whether the agent completed the task correctly.
- **Access-policy compliance** — whether the agent stayed inside the allowed
  actions (AOBench's core interest).
- **Cost / usage summary** — tokens and calls the agent spent.

The finding is the **access-policy verdict**: capable systems often answer the task
*and* comply, which is the interesting claim the benchmark is built to probe.

## 4. Read one example finding

```bash
aobench run --help
```

Run the same task with a different agent or environment to see how the finding
changes. Each run writes a JSON report under `runs/` — open it to see the raw
policy-evaluation trace, not just the summary line.

## 5. Where to go next

- [Quickstart](getting-started/quickstart.md) — what the quickstart output means
- [Evaluating your own agent](guides/evaluating-your-own-agent.md) — plug in your agent
- [Adapting tools & environments](guides/adapters-and-tools.md) — change the sandbox
- [Leaderboard](leaderboard.md) — compare published results
