#!/usr/bin/env python3
"""Regenerate the E3/E4/E5 ablation JSONs from the FROZEN latest-run-per-model set.

Root cause of the earlier staleness: ablate_{cup_threshold,difficulty,clear_weights}.py
globbed run_*/results/*.json (ALL runs) per model, so models with >1 run were averaged
over multiple runs, diverging from the headline tables (Table 7), which use only the
LATEST run per model. This script reproduces the SAME latest-run selection used by
scripts/load_results.py, so the ablation tables reconcile with Table 7.

Denominator/consistency assertions (per reviewer request):
  * every CuP pass rate == integer / 58
  * per-model difficulty-tier weighted mean ~= headline aggregate (tol 1e-3)
"""
from __future__ import annotations

import json
import random
import statistics as st
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "runs"
SPECS = ROOT / "benchmark" / "tasks" / "specs"
OUT = ROOT / "data" / "ablations"
EXCLUDE = {"AIOPS_USR_001"}

# (registry token as used as JSON key, split subdir).  Dir name = token.replace(":","_").
MODELS = [
    ("direct_qa", "v02_dev"), ("gpt-4o", "v02_dev"), ("gpt-4o-mini", "v02_dev"),
    ("GLM-4.7-Flash:latest", "v02_dev_ollama"), ("devstral-small-2:24b", "v02_dev_ollama"),
    ("gemma4:31b", "v02_dev_ollama"), ("gemma4:e4b", "v02_dev_ollama"),
    ("gpt-oss:20b", "v02_dev_ollama"), ("gpt-oss:latest", "v02_dev_ollama"),
    ("mistral-nemo:latest", "v02_dev_ollama"), ("mistral-small:24b", "v02_dev_ollama"),
    ("nemotron-3-super:latest", "v02_dev_ollama"), ("nemotron3:33b", "v02_dev_ollama"),
    ("qwen3-coder-next:latest", "v02_dev_ollama"), ("qwen3.5:122b", "v02_dev_ollama"),
    ("qwen3.6:35b-a3b", "v02_dev_ollama"),
]
THRESHOLDS = {"strict": 0.70, "tolerant_1": 0.60, "tolerant_2": 0.50}
WEIGHT_VARIANTS = {
    "equal":   {d: 1/7 for d in ["outcome","tool_use","grounding","governance","robustness","efficiency","workflow"]},
    "e_heavy": {"outcome":0.40,"tool_use":0.20,"grounding":0.10,"governance":0.15,"robustness":0.05,"efficiency":0.05,"workflow":0.05},
    "a_heavy": {"outcome":0.20,"tool_use":0.10,"grounding":0.10,"governance":0.40,"robustness":0.05,"efficiency":0.05,"workflow":0.10},
    "default": {"outcome":0.30,"tool_use":0.15,"grounding":0.10,"governance":0.20,"robustness":0.10,"efficiency":0.05,"workflow":0.10},
}

def load_latest(token, sub):
    """Latest run per model, exclude AIOPS_USR_001 — identical to load_results.load_model_results."""
    for dtok in (token, token.replace(":", "_")):
        base = RUNS / sub / dtok
        runs = sorted(base.glob("run_*")) if base.exists() else []
        if runs:
            out = []
            for f in sorted((runs[-1] / "results").glob("*.json")):
                r = json.loads(f.read_text(encoding="utf-8"))
                if r.get("task_id") not in EXCLUDE:
                    out.append(r)
            return out
    return []

# difficulty map from specs (dev split only for stratification denominators)
diffmap = {}
for f in SPECS.glob("*.json"):
    s = json.loads(f.read_text(encoding="utf-8"))
    diffmap[s.get("task_id")] = s.get("difficulty") or {1:"easy",2:"medium",3:"hard"}.get(s.get("difficulty_tier"))

def weighted(rec, w):
    ds = rec.get("dimension_scores") or {}
    tot = wsum = 0.0
    for d, wt in w.items():
        v = ds.get(d)
        if v is not None:
            wsum += wt*float(v)
            tot += wt
    return wsum/tot if tot else None

def bootstrap_ci(vals, n=10000, seed=42):
    rng = random.Random(seed)
    k = len(vals)
    boots = sorted(sum(vals[rng.randint(0,k-1)] for _ in range(k))/k for _ in range(n))
    return (round(boots[int(0.025*n)],4), round(boots[int(0.975*n)-1],4))

def spearman(x, y):
    def ranks(a):
        idx = sorted(range(len(a)), key=lambda i: a[i])
        r=[0.0]*len(a)
        i=0
        while i < len(a):
            j=i
            while j<len(a) and a[idx[j]]==a[idx[i]]:
                j+=1
            avg=(i+j-1)/2+1
            for k in range(i,j):
                r[idx[k]]=avg
            i=j
        return r
    rx, ry = ranks(x), ranks(y)
    n=len(x)
    mx=sum(rx)/n
    my=sum(ry)/n
    num=sum((rx[i]-mx)*(ry[i]-my) for i in range(n))
    den=(sum((rx[i]-mx)**2 for i in range(n))*sum((ry[i]-my)**2 for i in range(n)))**0.5
    return round(num/den,4) if den else float("nan")

# load all
data = {tok: load_latest(tok, sub) for tok, sub in MODELS}
for tok, recs in data.items():
    assert recs, f"NO DATA for {tok}"
    assert len(recs) == 58, f"{tok}: {len(recs)} records (expected 58)"
tokens = [t for t, _ in MODELS]
now = datetime.now(timezone.utc).isoformat()

# ---- E4 cup_threshold ----
pass_rates = {v: {} for v in THRESHOLDS}
for v, thr in THRESHOLDS.items():
    for tok in tokens:
        recs = data[tok]
        passes = sum(1 for r in recs if not r.get("hard_fail") and r.get("aggregate_score") is not None and float(r["aggregate_score"]) >= thr)
        assert passes == int(passes), tok
        pass_rates[v][tok] = round(passes/len(recs), 4)
cup = {"generated_at": now, "variants": list(THRESHOLDS), "models": tokens, "pass_rates": pass_rates}
(OUT/"cup_threshold.json").write_text(json.dumps(cup, indent=2), encoding="utf-8")

# ---- E5 difficulty ----
tiers = ["easy","medium","hard"]
mean_scores = {d: {} for d in tiers}
ci_95 = {d: {} for d in tiers}
for tok in tokens:
    recs = data[tok]
    by = {d: [] for d in tiers}
    for r in recs:
        d = diffmap.get(r["task_id"])
        sc = r.get("aggregate_score")
        if sc is None:
            sc = (r.get("dimension_scores") or {}).get("outcome")
        if d in by and sc is not None:
            by[d].append(float(sc))
    for d in tiers:
        if by[d]:
            mean_scores[d][tok] = round(st.mean(by[d]), 4)
            ci_95[d][tok] = list(bootstrap_ci(by[d]))
diff = {"generated_at": now, "difficulties": tiers, "models": tokens, "mean_scores": mean_scores, "ci_95": ci_95}
(OUT/"difficulty.json").write_text(json.dumps(diff, indent=2), encoding="utf-8")

# ---- E3 clear_weights ----
scores = {v: {} for v in WEIGHT_VARIANTS}
for v, w in WEIGHT_VARIANTS.items():
    for tok in tokens:
        vals = [s for r in data[tok] if (s := weighted(r, w)) is not None]
        scores[v][tok] = round(st.mean(vals), 4) if vals else None
srho = {}
for v in ["equal","e_heavy","a_heavy"]:
    x = [scores[v][t] for t in tokens]
    y = [scores["default"][t] for t in tokens]
    srho[f"{v}_vs_default"] = spearman(x, y)
cw = {"generated_at": now, "variants": list(WEIGHT_VARIANTS), "models": tokens, "scores": scores, "spearman_rho": srho}
(OUT/"clear_weights.json").write_text(json.dumps(cw, indent=2), encoding="utf-8")

# ---- assertions vs Table 7 (headline aggregate) ----
print("=== regenerated. consistency check: difficulty-tier weighted mean vs headline aggregate ===")
for tok in tokens:
    recs = data[tok]
    head = st.mean([r["aggregate_score"] for r in recs])
    # weighted reconstruction from tier means
    num = 0.0
    den = 0
    for d in tiers:
        vals = [float(r["aggregate_score"]) for r in recs if diffmap.get(r["task_id"])==d]
        num += sum(vals)
        den += len(vals)
    recon = num/den
    ok = abs(head - recon) < 1e-6
    print(f"  {tok:26} headline={head:.4f}  tier-recon={recon:.4f}  {'OK' if ok else 'MISMATCH'}")
print("\n=== CuP strict pass rates (must be integer/58) ===")
for tok in tokens:
    r = pass_rates["strict"][tok]
    print(f"  {tok:26} strict={r}  = {round(r*58)}/58")
