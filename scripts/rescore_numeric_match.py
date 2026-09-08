#!/usr/bin/env python3
"""Measure the ranking impact of fixing the numeric_match wiring bug.
Rescore the 4 numeric_match dev tasks across all 16 models from frozen traces
(no LLM). Corrected numeric_match behaves like 'numeric' mode."""
import json
import statistics as st
from pathlib import Path

import yaml

from aobench.schemas.task import TaskSpec
from aobench.scorers.outcome_scorer import _fuzzy_score, _numeric_match

ROOT=Path(__file__).resolve().parents[1]
SPECS=ROOT/"benchmark/tasks/specs"
rs=json.loads((ROOT/"RUNSET_v0.2.json").read_text(encoding="utf-8"))
profiles=yaml.safe_load((ROOT/"benchmark/configs/scoring_profiles.yaml").read_text(encoding="utf-8"))["profiles"]

# dev task set (58)
info=rs["dev"]["direct_qa"]
resdir=ROOT/"data/runs"/info["dir"]/info["run_id"]/"results"
tids=[t for t in (json.loads(f.read_text(encoding="utf-8"))["task_id"] for f in sorted(resdir.glob("*.json"))) if t!="AIOPS_USR_001"]

# numeric_match tasks + golds
nm={}
for t in tids:
    s=TaskSpec.model_validate(json.loads((SPECS/f"{t}.json").read_text(encoding="utf-8")))
    if s.eval_criteria and (s.eval_criteria.evaluation_mode or "").lower()=="numeric_match":
        nm[t]=s.eval_criteria.gold_answer.strip()
print(f"numeric_match tasks: {list(nm)}")

def corrected_outcome(pred, gold):
    """numeric_match -> behave like 'numeric' mode."""
    if not pred or not pred.strip():
        return 0.0
    ns=_numeric_match(pred.strip(), gold)
    if ns is None:
        return round(_fuzzy_score(pred.strip(), gold),4)
    return round(ns,4)

models=[m for m in rs["dev"]]
old_means={}
new_means={}
per_task_changes=[]
for m in models:
    d=rs["dev"][m]
    rdir=ROOT/"data/runs"/d["dir"]/d["run_id"]/"results"
    tdir=ROOT/"data/runs"/d["dir"]/d["run_id"]/"traces"
    # map task->result file
    rmap={}
    for f in rdir.glob("*.json"):
        r=json.loads(f.read_text(encoding="utf-8"))
        rmap[r["task_id"]]=r
    aggs_old=[]
    aggs_new=[]
    for t in tids:
        r=rmap[t]
        agg=r.get("aggregate_score") or 0.0
        aggs_old.append(agg)
        if t in nm and not r.get("hard_fail") and r.get("dimension_scores",{}).get("outcome")==0.5:
            # load trace answer
            tf=None
            for cand in tdir.glob(f"{t}*trace.json"):
                tf=cand
                break
            ans=""
            if tf:
                tr=json.loads(tf.read_text(encoding="utf-8"))
                ans=tr.get("final_answer") or ""
            new_out=corrected_outcome(ans, nm[t])
            prof=profiles[r["weight_profile_name"]]["weights"]
            w=prof["outcome"]
            # aggregate normalized over active weights summing to 1; delta = w*(new-old_outcome)
            new_agg=agg + w*(new_out-0.5)
            new_agg=max(0.0,min(1.0,new_agg))
            aggs_new.append(new_agg)
            per_task_changes.append((m,t,0.5,new_out,agg,round(new_agg,4)))
        else:
            aggs_new.append(agg)
    old_means[m]=st.mean(aggs_old)
    new_means[m]=st.mean(aggs_new)

# rankings
def spearman(a,b):
    def rank(x):
        idx=sorted(range(len(x)),key=lambda i:x[i])
        r=[0]*len(x)
        for pos,i in enumerate(idx):
            r[i]=pos
        return r
    ra,rb=rank(a),rank(b)
    n=len(a)
    ma=sum(ra)/n
    mb=sum(rb)/n
    num=sum((ra[i]-ma)*(rb[i]-mb) for i in range(n))
    den=(sum((ra[i]-ma)**2 for i in range(n))*sum((rb[i]-mb)**2 for i in range(n)))**.5
    return num/den if den else 1.0

print("\nper-task corrections (model, task, old_out->new_out, old_agg->new_agg):")
for c in per_task_changes:
    print(f"  {c[0]:22} {c[1]:14} {c[2]}->{c[3]:.3f}  agg {c[4]:.4f}->{c[5]:.4f}")

order_old=sorted(models,key=lambda m:-old_means[m])
order_new=sorted(models,key=lambda m:-new_means[m])
print("\nmean aggregate old vs new (sorted by old):")
for m in order_old:
    d=new_means[m]-old_means[m]
    print(f"  {m:22} {old_means[m]:.4f} -> {new_means[m]:.4f}  (Δ{d:+.4f})  rank_old={order_old.index(m)+1} rank_new={order_new.index(m)+1}")
xs=[old_means[m] for m in models]
ys=[new_means[m] for m in models]
print(f"\nSpearman(old,new) ranking = {spearman(xs,ys):.4f}")
print(f"max |Δ mean aggregate| = {max(abs(new_means[m]-old_means[m]) for m in models):.4f}")
