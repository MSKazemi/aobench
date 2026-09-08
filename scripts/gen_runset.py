#!/usr/bin/env python3
"""Freeze the exact run IDs used for every v0.2 headline number into a single
manifest, so reproduction pins concrete runs instead of re-resolving "latest".
Mirrors the latest-run-per-model selection in scripts/load_results.py."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/runs"

# (json key/token, split-subdir)
DEV = [
    ("direct_qa", "v02_dev"), ("gpt-4o", "v02_dev"), ("gpt-4o-mini", "v02_dev"),
    ("GLM-4.7-Flash:latest", "v02_dev_ollama"), ("devstral-small-2:24b", "v02_dev_ollama"),
    ("gemma4:31b", "v02_dev_ollama"), ("gemma4:e4b", "v02_dev_ollama"),
    ("gpt-oss:20b", "v02_dev_ollama"), ("gpt-oss:latest", "v02_dev_ollama"),
    ("mistral-nemo:latest", "v02_dev_ollama"), ("mistral-small:24b", "v02_dev_ollama"),
    ("nemotron-3-super:latest", "v02_dev_ollama"), ("nemotron3:33b", "v02_dev_ollama"),
    ("qwen3-coder-next:latest", "v02_dev_ollama"), ("qwen3.5:122b", "v02_dev_ollama"),
    ("qwen3.6:35b-a3b", "v02_dev_ollama"),
]
TEST = [("direct_qa", "v02_test"), ("gpt-4o", "v02_test"), ("gpt-4o-mini", "v02_test")]

def resolve(token, sub):
    for dtok in (token, token.replace(":", "_")):
        base = RUNS / sub / dtok
        runs = sorted(base.glob("run_*")) if base.exists() else []
        if runs:
            last = runs[-1]
            n = len(list((last/"results").glob("*.json")))
            return {"dir": f"{sub}/{dtok}", "run_id": last.name, "n_results": n}
    return None

def build(models):
    out = {}
    for tok, sub in models:
        r = resolve(tok, sub)
        assert r, f"no run for {tok} in {sub}"
        out[tok] = r
    return out

manifest = {
    "runset": "v0.2",
    "description": "Frozen run IDs for every AOBench v0.2 headline number. "
                   "Each model resolves to exactly one run directory; "
                   "AIOPS_USR_001 is excluded from the 59-task dev set (58 scored).",
    "selection_rule": "one run per model; the run_id recorded here is authoritative "
                      "(supersedes any later 'latest' run added to the same directory).",
    "excluded_tasks": ["AIOPS_USR_001"],
    "dev": build(DEV),
    "test": build(TEST),
}
p = ROOT / "RUNSET_v0.2.json"
p.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"wrote {p}")
print(f"dev models: {len(manifest['dev'])}  test models: {len(manifest['test'])}")
for k, v in list(manifest["dev"].items())[:3]:
    print(f"  {k}: {v['run_id']} ({v['n_results']} results)")
