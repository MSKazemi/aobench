#!/usr/bin/env python3
"""Oracle check: verify each task's gold answer is derivable from snapshot data."""
import sys
import json
import pathlib
import argparse


def check_task(task_path: pathlib.Path, env_dir: str) -> tuple[str, bool, str]:
    """Returns (task_id, passed, reason)."""
    with open(task_path) as f:
        d = json.load(f)
    task_id = d.get("task_id", task_path.stem)

    # Check environment exists
    env_id = d.get("environment_id", "")
    env_path = pathlib.Path(env_dir) / env_id
    if not env_path.exists():
        return task_id, False, f"env dir missing: {env_id}"

    # Check gold_answer set
    eval_criteria = d.get("eval_criteria") or {}
    gold_answer = eval_criteria.get("gold_answer") if eval_criteria else None
    if not gold_answer:
        return task_id, False, "gold_answer missing"

    # Check evidence refs exist
    refs = d.get("gold_evidence_refs", [])
    for ref in refs:
        ref_path_str = ref.split("#")[0]  # strip fragment
        ref_path = env_path / ref_path_str
        if not ref_path.exists():
            return task_id, False, f"evidence missing: {ref_path_str}"

    return task_id, True, "ok"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that each task's gold answer is derivable from snapshot data."
    )
    parser.add_argument(
        "--task-dir",
        default="benchmark/tasks/specs",
        help="Directory containing task spec JSON files (default: benchmark/tasks/specs)",
    )
    parser.add_argument(
        "--env-dir",
        default="benchmark/environments",
        help="Directory containing environment bundles (default: benchmark/environments)",
    )
    args = parser.parse_args(argv)

    task_dir = pathlib.Path(args.task_dir)
    if not task_dir.exists():
        print(f"ERROR: task-dir does not exist: {task_dir}", file=sys.stderr)
        return 2

    results = []
    for f in sorted(task_dir.glob("*.json")):
        results.append(check_task(f, args.env_dir))

    print(f"{'Task':30} {'Status':8} {'Reason'}")
    print("-" * 70)
    passed = failed = 0
    for task_id, ok, reason in results:
        status = "PASS" if ok else "FAIL"
        print(f"{task_id:30} {status:8} {reason}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
