#!/usr/bin/env python3
"""Independence check: detect near-duplicate tasks by cosine similarity of feature vectors."""
import sys
import json
import math
import pathlib
import argparse

_DIFFICULTY_TO_TIER = {"easy": 1, "medium": 2, "hard": 3, "adversarial": 3}


def _build_vector(d: dict) -> list[float]:
    """Build a 5-component normalised feature vector for a task spec dict.

    Components (all clipped to [0, 1]):
      0: difficulty_tier / 3
      1: len(gold_evidence_refs) / 10
      2: len(query_text) / 500
      3: len(gold_answer) / 1000  (empty string if missing)
      4: 1.0 if "slurm" in allowed_tools else 0.0
    """
    difficulty = d.get("difficulty", "easy")
    tier = _DIFFICULTY_TO_TIER.get(difficulty, 1)
    v0 = min(tier / 3.0, 1.0)

    refs = d.get("gold_evidence_refs") or []
    v1 = min(len(refs) / 10.0, 1.0)

    query = d.get("query_text") or ""
    v2 = min(len(query) / 500.0, 1.0)

    eval_criteria = d.get("eval_criteria") or {}
    gold_answer = eval_criteria.get("gold_answer") or ""
    v3 = min(len(gold_answer) / 1000.0, 1.0)

    allowed_tools = d.get("allowed_tools") or []
    v4 = 1.0 if "slurm" in allowed_tools else 0.0

    return [v0, v1, v2, v3, v4]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect near-duplicate tasks by cosine similarity of feature vectors."
    )
    parser.add_argument(
        "--task-dir",
        default="benchmark/tasks/specs",
        help="Directory containing task spec JSON files (default: benchmark/tasks/specs)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="Cosine similarity threshold above which tasks are flagged (default: 0.95)",
    )
    args = parser.parse_args(argv)

    task_dir = pathlib.Path(args.task_dir)
    if not task_dir.exists():
        print(f"ERROR: task-dir does not exist: {task_dir}", file=sys.stderr)
        return 2

    # Load all specs
    specs: list[tuple[str, list[float]]] = []
    for f in sorted(task_dir.glob("*.json")):
        with open(f) as fh:
            d = json.load(fh)
        task_id = d.get("task_id", f.stem)
        vec = _build_vector(d)
        specs.append((task_id, vec))

    if not specs:
        print("No task specs found.")
        return 0

    # Compare all pairs
    flagged: list[tuple[str, str, float]] = []
    for i in range(len(specs)):
        for j in range(i + 1, len(specs)):
            tid_a, vec_a = specs[i]
            tid_b, vec_b = specs[j]
            sim = _cosine_similarity(vec_a, vec_b)
            if sim >= args.threshold:
                flagged.append((tid_a, tid_b, sim))

    if flagged:
        print(f"WARNING: {len(flagged)} near-duplicate pair(s) found (threshold={args.threshold}):")
        print(f"\n{'Task A':30} {'Task B':30} {'Similarity':>12}")
        print("-" * 74)
        for tid_a, tid_b, sim in flagged:
            print(f"{tid_a:30} {tid_b:30} {sim:>12.4f}")
        print(f"\nTotal tasks checked: {len(specs)}")
        return 1

    print(f"OK: no near-duplicate pairs found (threshold={args.threshold}, tasks checked={len(specs)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
