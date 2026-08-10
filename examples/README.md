# AOBench examples

Four runnable scripts, in the order they are worth reading. **All of them run offline
with no API key** — they use the `direct_qa` baseline, so you can execute every one
immediately after `make install`.

```bash
python examples/01_hello_aobench.py
python examples/02_score_a_trace.py
python examples/03_custom_adapter.py
python examples/04_ci_gate.py data/runs/<run_id> --min-score 0.30
python examples/05_compare_two_adapters.py
```

| Example | Shows |
|---|---|
| [`01_hello_aobench.py`](01_hello_aobench.py) | Load the corpus and run one task from Python, without the CLI |
| [`02_score_a_trace.py`](02_score_a_trace.py) | Score a trace you produced elsewhere — the "bring your own agent" path |
| [`03_custom_adapter.py`](03_custom_adapter.py) | Write an adapter for your own agent, complete and under 60 lines |
| [`04_ci_gate.py`](04_ci_gate.py) | Turn a run into a pass/fail CI gate, hard-fails counted separately |
| [`05_compare_two_adapters.py`](05_compare_two_adapters.py) | Run two offline baselines, then compare their scores dimension by dimension |

These are tested: `tests/test_examples.py` executes each one, so an example that
stops working breaks the build rather than quietly rotting.

## Where to go next

- [Quickstart](https://mskazemi.com/aobench/latest/getting-started/quickstart/) — the CLI path
- [Evaluate your own agent](https://mskazemi.com/aobench/latest/guides/evaluating-your-own-agent/) — the three integration routes
- [CI integration](https://mskazemi.com/aobench/latest/guides/ci-integration/) — the full GitHub Actions setup

**Missing an example you needed?** That is a documentation bug —
[tell us](https://github.com/MSKazemi/aobench/issues/new/choose), or add it: examples
are an excellent first contribution.
