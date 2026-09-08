#!/usr/bin/env python3
"""RUNSET-pinned recompute-and-diff verifier for the AOBench paper tables.

Reads ONLY RUNSET_v0.2.json to resolve runs (never 'latest'/glob/mtime),
recomputes every headline per-model quantity from the frozen per-task result
files with the final scorer (applying the numeric_match correction), and diffs
against the values parsed from a LaTeX manuscript ($AOBENCH_PAPER_TEX). Exits non-zero (fails
the build) if any inline value diverges from frozen truth beyond tolerance.

Deterministic quantities checked (point estimates, rng-independent):
  Table 7  : Aggregate, Outcome, Tool Use, Assurance, Efficiency, Grounding
  Table 15 : cup strict/tolerant-1/tolerant-2 pass rates
  Table 16 : difficulty easy/medium/hard tier means
Structural checks: 16 systems, 58 unique dev tasks each, identical task-ID set,
AIOPS_USR_001 absent, no duplicate task IDs.

Aggregate 95% CIs (Table 7) are bootstrap and rng/order-dependent; this verifier
recomputes them with a fixed standalone seed and reports them for reference,
but does not fail the build on CI mismatch (documented limitation).

Usage:
    uv run python scripts/verify_tables_runset.py [--tex PATH] [--tol 0.0006]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics as st
import sys
from pathlib import Path

import numpy as np
import yaml

from aobench.schemas.task import TaskSpec
from aobench.scorers.outcome_scorer import _fuzzy_score, _numeric_match

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "benchmark/tasks/specs"
CUP_TAU = {"strict": 0.70, "tolerant_1": 0.60, "tolerant_2": 0.50}

# RUNSET model key -> exact paper label (Table 7 row name)
LABELS = {
    "gpt-4o": "GPT-4o",
    "gpt-4o-mini": "GPT-4o-mini",
    "qwen3.6:35b-a3b": "Qwen3.6 35B-A3B (MoE)",
    "qwen3.5:122b": "Qwen3.5 122B",
    "mistral-nemo:latest": "Mistral NeMo 12B",
    "nemotron-3-super:latest": "Nemotron-3 Super 120B",
    "GLM-4.7-Flash:latest": "GLM-4.7-Flash",
    "nemotron3:33b": "Nemotron-3 33B",
    "devstral-small-2:24b": "Devstral Small 2 24B",
    "qwen3-coder-next:latest": "Qwen3-Coder-Next 80B",
    "gpt-oss:20b": "GPT-OSS 20B",
    "gemma4:e4b": "Gemma 4 E4B",
    "gpt-oss:latest": "GPT-OSS 20B (latest)",
    "mistral-small:24b": "Mistral Small 24B",
    "gemma4:31b": "Gemma 4 31B",
    "direct_qa": "Direct QA (baseline)",
}


def corrected_outcome(pred: str, gold: str) -> float:
    """numeric_match wiring fix: behave like 'numeric' mode, fuzzy fallback."""
    if not pred or not pred.strip():
        return 0.0
    ns = _numeric_match(pred.strip(), gold)
    if ns is None:
        return round(_fuzzy_score(pred.strip(), gold), 4)
    return round(ns, 4)


def _mean(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def r3(x: float) -> float:
    """Round half-up to 3 decimals (LaTeX/standard convention, not banker's)."""
    import math
    return math.floor(x * 1000 + 0.5) / 1000


def recompute() -> tuple[dict, list[str]]:
    rs = json.loads((ROOT / "RUNSET_v0.2.json").read_text(encoding="utf-8"))
    profiles = yaml.safe_load((ROOT / "benchmark/configs/scoring_profiles.yaml").read_text(encoding="utf-8"))["profiles"]

    struct: list[str] = []
    # dev task set from direct_qa (authoritative), AIOPS_USR_001 excluded
    info = rs["dev"]["direct_qa"]
    resdir = ROOT / "data/runs" / info["dir"] / info["run_id"] / "results"
    tids = sorted({json.loads(f.read_text(encoding="utf-8"))["task_id"] for f in resdir.glob("*.json")} - {"AIOPS_USR_001"})
    if len(tids) != 58:
        struct.append(f"expected 58 dev tasks, got {len(tids)}")
    if "AIOPS_USR_001" in tids:
        struct.append("AIOPS_USR_001 present in scored set")

    # numeric_match tasks + golds; difficulty tier per task (from spec)
    nm: dict[str, str] = {}
    difficulty: dict[str, str] = {}
    for t in tids:
        spec = json.loads((SPECS / f"{t}.json").read_text(encoding="utf-8"))
        difficulty[t] = (spec.get("difficulty") or "").lower()
        s = TaskSpec.model_validate(spec)
        if s.eval_criteria and (s.eval_criteria.evaluation_mode or "").lower() == "numeric_match":
            nm[t] = s.eval_criteria.gold_answer.strip()

    models = list(rs["dev"])
    if len(models) != 16:
        struct.append(f"expected 16 systems, got {len(models)}")

    out: dict[str, dict] = {}
    for m in models:
        d = rs["dev"][m]
        rdir = ROOT / "data/runs" / d["dir"] / d["run_id"] / "results"
        tdir = ROOT / "data/runs" / d["dir"] / d["run_id"] / "traces"
        rmap = {}
        for f in rdir.glob("*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            rmap[r["task_id"]] = r
        task_ids = sorted(rmap)
        if len(task_ids) != len(set(task_ids)):
            struct.append(f"{m}: duplicate task IDs")
        missing = set(tids) - set(rmap)
        if missing:
            struct.append(f"{m}: missing {len(missing)} dev tasks")

        outc, tu, eff, grd, assur, aggs, cupsc = [], [], [], [], [], [], []
        cup = {k: 0 for k in CUP_TAU}
        tiers: dict[str, list] = {"easy": [], "medium": [], "hard": []}
        for t in tids:
            r = rmap[t]
            ds = r.get("dimension_scores", {})
            o = ds.get("outcome")
            agg = r.get("aggregate_score") or 0.0
            cs = r.get("cup_score")
            hf = bool(r.get("hard_fail"))
            if t in nm and not hf and o == 0.5:
                ans = ""
                for cand in tdir.glob(f"{t}*trace.json"):
                    tr = json.loads(cand.read_text(encoding="utf-8"))
                    ans = tr.get("final_answer") or ""
                    break
                new_o = corrected_outcome(ans, nm[t])
                w = profiles[r["weight_profile_name"]]["weights"]["outcome"]
                agg = max(0.0, min(1.0, agg + w * (new_o - 0.5)))
                # cup_score is the violation-gated Outcome; if the task had no
                # violation cup==outcome, so it tracks the corrected outcome.
                if cs is not None and abs(cs - 0.5) < 1e-9:
                    cs = new_o
                o = new_o
            outc.append(o)
            tu.append(ds.get("tool_use"))
            eff.append(ds.get("efficiency"))
            grd.append(ds.get("grounding"))
            cupsc.append(cs)
            if r.get("engaged"):
                ge = r.get("governance_eng")
                if ge is not None:
                    assur.append(ge)
            aggs.append(agg)
            for k, tau in CUP_TAU.items():
                if not hf and agg >= tau:
                    cup[k] += 1
            tier = difficulty.get(t, "")
            if tier in tiers:
                tiers[tier].append(agg)

        n = len(aggs)
        rng = np.random.default_rng(42)
        arr = np.array(aggs)
        boot = np.array([np.mean(rng.choice(arr, size=n, replace=True)) for _ in range(10000)])

        def tier_ci(vals):
            if not vals:
                return None
            rr = np.random.default_rng(42)
            a = np.array(vals)
            b = np.array([np.mean(rr.choice(a, size=len(a), replace=True)) for _ in range(10000)])
            return (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))

        out[m] = {
            "label": LABELS.get(m, m),
            "n": n,
            "aggregate": st.mean(aggs),
            "ci": (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))),
            "outcome": _mean(outc),
            "tool_use": _mean(tu),
            "assurance": _mean(assur) if assur else None,
            "efficiency": _mean(eff),
            "grounding": _mean(grd),
            "estar": _mean(cupsc),
            "cup": {k: v / n for k, v in cup.items()},
            "tiers": {k: (_mean(v) if v else None) for k, v in tiers.items()},
            "tier_ci": {k: tier_ci(v) for k, v in tiers.items()},
            "tier_n": {k: len(v) for k, v in tiers.items()},
        }
    return out, struct


def parse_tex_main(tex: str) -> dict[str, dict]:
    m = re.search(r"\\label\{tab:main\}(.*?)\\end\{tabular\}", tex, re.DOTALL)
    rows = {}
    for line in (m.group(1).splitlines() if m else []):
        mm = re.match(r"\s*([A-Za-z0-9 .\-\(\)]+?)\s*&\s*([0-9.]+) \[([0-9.]+), ([0-9.]+)\] & ([0-9.]+) & ([0-9.]+) & ([0-9.]+|\\,---) & ([0-9.]+) & ([0-9.]+)", line)
        if mm:
            g = mm.groups()
            rows[g[0].strip()] = {
                "aggregate": float(g[1]), "ci": (float(g[2]), float(g[3])),
                "outcome": float(g[4]), "tool_use": float(g[5]),
                "assurance": None if "---" in g[6] else float(g[6]),
                "efficiency": float(g[7]), "grounding": float(g[8]),
            }
    return rows


def parse_tex_generic(tex: str, label: str, ncols: int) -> dict[str, tuple]:
    m = re.search(r"\\label\{" + re.escape(label) + r"\}(.*?)\\end\{tabular\}", tex, re.DOTALL)
    rows = {}
    for line in (m.group(1).splitlines() if m else []):
        mm = re.match(r"\s*([A-Za-z0-9 .\-\(\)]+?)\s*&\s*(.+?)\\\\", line)
        if not mm:
            continue
        name = mm.group(1).strip()
        nums = re.findall(r"[0-9]+\.[0-9]+", mm.group(2))
        if len(nums) >= ncols:
            rows[name] = tuple(float(x) for x in nums)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tex",
        default=os.environ.get("AOBENCH_PAPER_TEX", ""),
        help="Path to a LaTeX manuscript whose result tables should be verified "
        "against the frozen run set. Defaults to $AOBENCH_PAPER_TEX.",
    )
    # 0.0015 tolerates 3-decimal display/rounding-convention artifacts (one ULP
    # at 3 dp), matching assert_tables.py; only genuine drift (> ~0.001) fails.
    ap.add_argument("--tol", type=float, default=0.0015)
    args = ap.parse_args()

    comp, struct = recompute()
    tex = Path(args.tex).read_text(encoding="utf-8")
    main_rows = parse_tex_main(tex)
    cup_rows = parse_tex_generic(tex, "tab:abl_cup_threshold", 3)   # strict, tol1, tol2
    dif_rows = parse_tex_generic(tex, "tab:abl_difficulty", 6)      # easy,ci,ci, med,ci,ci, hard,ci,ci

    fails: list[str] = list(struct)
    print(f"{'model':26} {'agg':>7} {'out':>7} {'tool':>7} {'assur':>7} {'eff':>7} {'grnd':>7}   inline-agg  Δagg")
    for c in comp.values():
        lab = c["label"]
        inl = main_rows.get(lab)
        tag = ""
        if inl:
            for dim in ("aggregate", "outcome", "tool_use", "efficiency", "grounding"):
                if c[dim] is not None and abs(r3(c[dim]) - inl[dim]) > args.tol:
                    fails.append(f"[T7] {lab}: {dim} frozen={c[dim]:.4f} (->{r3(c[dim])}) != tex {inl[dim]}")
            if (
                c["assurance"] is not None
                and inl["assurance"] is not None
                and abs(r3(c["assurance"]) - inl["assurance"]) > args.tol
            ):
                fails.append(f"[T7] {lab}: assurance frozen={c['assurance']:.4f} != tex {inl['assurance']}")
            tag = f"  tex={inl['aggregate']:.3f}  Δ={r3(c['aggregate'])-inl['aggregate']:+.3f}"
        # T15 cup rates
        cinl = cup_rows.get(lab)
        if cinl:
            for k, v in zip(("strict", "tolerant_1", "tolerant_2"), cinl):
                if abs(r3(c["cup"][k]) - v) > args.tol:
                    fails.append(f"[T15] {lab}: {k} frozen={c['cup'][k]:.3f} != tex {v}")
        # T16 difficulty tier means (point estimates only, cols 0,3,6)
        dinl = dif_rows.get(lab)
        if dinl:
            for tier, idx in (("easy", 0), ("medium", 3), ("hard", 6)):
                fv = c["tiers"][tier]
                if fv is not None and abs(r3(fv) - dinl[idx]) > args.tol:
                    fails.append(f"[T16] {lab}: {tier} frozen={fv:.4f} != tex {dinl[idx]}")
        a = c["assurance"]
        print(f"{lab:26} {c['aggregate']:.4f} {c['outcome'] or 0:.4f} {c['tool_use'] or 0:.4f} "
              f"{(a if a is not None else float('nan')):.4f} {c['efficiency'] or 0:.4f} {c['grounding'] or 0:.4f}{tag}")

    # Focused dump of any model whose frozen values diverge (for the fix)
    print("\n-- corrected detail for mismatched rows --")
    flagged = {re.match(r"\[[^]]+\] ([^:]+):", f).group(1) for f in fails if f.startswith("[")}
    for c in comp.values():
        if c["label"] in flagged:
            print(f"{c['label']}: agg={c['aggregate']:.4f} CI=[{c['ci'][0]:.4f},{c['ci'][1]:.4f}] "
                  f"outcome={c['outcome']:.4f} E*={c['estar']:.4f} R(tol2)={c['cup']['tolerant_2']:.4f}")
            print(f"    cup strict/t1/t2 = {c['cup']['strict']:.4f}/{c['cup']['tolerant_1']:.4f}/{c['cup']['tolerant_2']:.4f}")
            for tier in ("easy", "medium", "hard"):
                tc = c["tier_ci"][tier]
                tv = c["tiers"][tier]
                print(f"    {tier}: {tv:.4f} CI=[{tc[0]:.4f},{tc[1]:.4f}] (n={c['tier_n'][tier]})" if tv is not None else f"    {tier}: --")

    if fails:
        print("\nVERIFY FAILED:")
        for f in fails:
            print("  -", f)
        return 1
    print("\nVERIFY: all inline point estimates (T7/T15/T16) match frozen truth within tol.")
    return 0


def _f(x):
    return f"{x:.3f}" if x is not None else "--"


if __name__ == "__main__":
    sys.exit(main())
