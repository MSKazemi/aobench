"""make_paper_table3.py — Table 3: Role × QCAT heatmap for v0.2 paper.

Input:  data/runs/v02_dev/<model>/run_*/results/*.json
Output: Two Markdown heatmap tables — GPT-4o absolute scores + delta vs direct_qa.
"""

import json
import pathlib
import statistics

V02_BASE = pathlib.Path("data/runs/v02_dev")

ROLES = ["scientific_user", "sysadmin", "facility_admin", "researcher", "system_designer"]
ROLE_LABELS = {
    "scientific_user": "scientific_user",
    "sysadmin":        "sysadmin",
    "facility_admin":  "facility_admin",
    "researcher":      "researcher",
    "system_designer": "system_designer",
}
QCATS = ["AIOPS", "ARCH", "DATA", "DOCS", "ENERGY", "FAC", "JOB", "MON", "SEC", "USR"]


def load_results(model_token: str) -> list[dict]:
    """Load results from the most recent run directory for the given model."""
    model_dir = V02_BASE / model_token
    run_dirs = sorted(model_dir.glob("run_*"))
    if not run_dirs:
        return []
    latest = run_dirs[-1]
    results = []
    for f in sorted(latest.glob("results/*.json")):
        try:
            results.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return results


def build_slices(results: list[dict]) -> dict[str, dict[str, dict]]:
    """Return slices[role][qcat] = {mean_score, count}."""
    from collections import defaultdict
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in results:
        role = r.get("role") or ""
        qcat = r.get("task_category") or ""
        score = r.get("aggregate_score")
        if role and qcat and score is not None:
            buckets[role][qcat].append(float(score))
    slices: dict[str, dict[str, dict]] = {}
    for role, qcat_map in buckets.items():
        slices[role] = {}
        for qcat, scores in qcat_map.items():
            slices[role][qcat] = {
                "mean_score": statistics.mean(scores),
                "count": len(scores),
            }
    return slices


results_a = load_results("direct_qa")
results_b = load_results("gpt-4o")

slices_a = build_slices(results_a)
slices_b = build_slices(results_b)

# Only keep QCATs that appear in v02 data
present_qcats = sorted({q for s in (slices_a, slices_b) for role_data in s.values() for q in role_data})


def cell_b(role, qcat) -> str:
    s = slices_b.get(role, {}).get(qcat)
    if s is None:
        return "—"
    return f"{s['mean_score']:.3f} (n={s['count']})"


def cell_delta(role, qcat) -> str:
    sa = slices_a.get(role, {}).get(qcat)
    sb = slices_b.get(role, {}).get(qcat)
    if sa is None or sb is None:
        return "—"
    delta = sb["mean_score"] - sa["mean_score"]
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.3f} (n={sb['count']})"


# ── Heatmap 1: GPT-4o absolute scores ───────────────────────────────────────
print("## Table 3a — GPT-4o Mean Score by Role × QCAT\n")
header = "| Role | " + " | ".join(present_qcats) + " |"
sep    = "|------|" + "|".join(["------"] * len(present_qcats)) + "|"
print(header)
print(sep)
for role in ROLES:
    if not any(slices_b.get(role, {}).get(q) for q in present_qcats):
        continue
    cells = [cell_b(role, q) for q in present_qcats]
    print(f"| {role} | " + " | ".join(cells) + " |")

# ── Heatmap 2: delta vs direct_qa ───────────────────────────────────────────
print("\n## Table 3b — GPT-4o delta vs direct_qa (GPT-4o − direct_qa)\n")
print(header)
print(sep)
for role in ROLES:
    if not any(slices_b.get(role, {}).get(q) for q in present_qcats):
        continue
    cells = [cell_delta(role, q) for q in present_qcats]
    print(f"| {role} | " + " | ".join(cells) + " |")
