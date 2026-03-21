"""Generate Table 3 — Role × QCAT heatmap (GPT-4o scores + delta vs direct_qa).

Input:  data/reports/v01_compare_directqa_vs_gpt4o.json
Output: Two Markdown heatmap tables.
"""

import json
import pathlib

COMPARE_PATH = pathlib.Path("data/reports/v01_compare_directqa_vs_gpt4o.json")

ROLES = ["scientific_user", "sysadmin", "facility_admin"]
ROLE_LABELS = {"scientific_user": "scientific_user", "sysadmin": "sysadmin", "facility_admin": "facility_admin"}
QCATS = ["ENERGY", "JOB", "MON"]

d = json.loads(COMPARE_PATH.read_text())
slices_a = d["slices_a"]   # direct_qa
slices_b = d["slices_b"]   # GPT-4o


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
header = "| Role | " + " | ".join(QCATS) + " |"
sep    = "|------|" + "|".join(["------"] * len(QCATS)) + "|"
print(header)
print(sep)
for role in ROLES:
    cells = [cell_b(role, q) for q in QCATS]
    print(f"| {role} | " + " | ".join(cells) + " |")

# ── Heatmap 2: delta vs direct_qa ───────────────────────────────────────────
print("\n## Table 3b — GPT-4o delta vs direct_qa (GPT-4o − direct_qa)\n")
print(header)
print(sep)
for role in ROLES:
    cells = [cell_delta(role, q) for q in QCATS]
    print(f"| {role} | " + " | ".join(cells) + " |")
