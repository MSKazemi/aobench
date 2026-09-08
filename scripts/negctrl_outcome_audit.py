#!/usr/bin/env python3
"""Negative-control audit of the frozen OutcomeScorer on the 58 dev tasks.
No LLM, no rerun: feed fixed answers and read the deterministic Outcome score."""
import json
from collections import Counter
from pathlib import Path

from aobench.schemas.task import TaskSpec
from aobench.schemas.trace import Trace
from aobench.scorers.outcome_scorer import OutcomeScorer

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "benchmark/tasks/specs"
rs = json.loads((ROOT/"RUNSET_v0.2.json").read_text(encoding="utf-8"))
info = rs["dev"]["direct_qa"]
resdir = ROOT/"data/runs"/info["dir"]/info["run_id"]/"results"

# 58 scored dev task ids (exclude AIOPS_USR_001)
task_ids = []
for f in sorted(resdir.glob("*.json")):
    tid = json.loads(f.read_text(encoding="utf-8"))["task_id"]
    if tid != "AIOPS_USR_001":
        task_ids.append(tid)
print(f"dev tasks: {len(task_ids)}")

scorer = OutcomeScorer()
specs = {t: TaskSpec.model_validate(json.loads((SPECS/f"{t}.json").read_text(encoding="utf-8"))) for t in task_ids}

def mk_trace(task, answer):
    return Trace(trace_id="t", run_id="r", task_id=task.task_id, role=task.role,
                 environment_id=task.environment_id, adapter_name="direct_qa",
                 final_answer=answer)

# a shuffled gold answer from another task (use each task's gold shifted by 1)
gold_of = {}
for t in task_ids:
    ga = getattr(specs[t], "gold_answer", None)
    gold_of[t] = (ga if isinstance(ga, str) else (str(ga) if ga is not None else "")) or ""

controls = {
    "empty": lambda t: "",
    "placeholder": lambda t: "[DirectQA: no answer provided]",
    "irrelevant": lambda t: "The mitochondria is the powerhouse of the cell.",
    "shuffled_gold": lambda t: gold_of[task_ids[(task_ids.index(t)+1) % len(task_ids)]],
}

# also record evaluation_mode distribution
modes = Counter(getattr(specs[t], "evaluation_mode", None) for t in task_ids)
print("evaluation_mode distribution (58 dev):", dict(modes))

for label, fn in controls.items():
    scores = []
    n05 = n0 = 0
    for t in task_ids:
        s = scorer.score(specs[t], mk_trace(specs[t], fn(t))).score
        scores.append(s)
        if abs(s-0.5) < 1e-9:
            n05 += 1
        if s == 0.0:
            n0 += 1
    m = sum(scores)/len(scores)
    print(f"  {label:14} mean={m:.4f} min={min(scores):.3f} max={max(scores):.3f} n(=0.5)={n05} n(=0)={n0}")

# which tasks give exactly 0.5 for placeholder, and their modes
print("\nnumeric_match tasks (the exact-0.5 source):")
for t in task_ids:
    if getattr(specs[t], "evaluation_mode", None) == "numeric_match":
        print(f"  {t}")
