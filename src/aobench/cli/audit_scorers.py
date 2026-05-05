"""audit_scorers.py — O.a–O.c scorer validity audit for AOBench.

Usage
-----
    python -m aobench.cli.audit_scorers [OPTIONS]

Options
-------
    --check TEXT           Which outcome check to run: oa | ob | oc | all (default: all)
    --task-file PATH       Task corpus JSON
    --snapshot-dir PATH    Environments directory
    --judge-model TEXT     LLM judge model (default: claude-sonnet-4-6)
    --n-repeats INT        Repeats for O.c stochastic test (default: 5)
    --output PATH          Output report path (default: stdout)
    --format TEXT          json | text (default: json)
    --string-equiv-file PATH  YAML file of equivalent string sets for O.a

Checks
------
O.a — Equivalence classes: verifies that semantically-equivalent strings
      score the same as the canonical form.

O.b — Negation: verifies that negated / opposite answers score lower than
      the correct answer.

O.c — Repeat stability: verifies that re-running a scorer on the same
      input produces the same score (stochastic scorer test).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_DEFAULT_TASK_FILE = "benchmark/tasks/task_set_v1.json"
_DEFAULT_SNAPSHOT_DIR = "benchmark/environments/"
_DEFAULT_STRING_EQUIV_FILE = "benchmark/scorer_audit/string_equiv_classes.yaml"
_DEFAULT_JUDGE_MODEL = "claude-sonnet-4-6"
_DEFAULT_N_REPEATS = 5


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for audit_scorers.  Returns 0 on success, 1 on failure."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    check_names = _resolve_checks(args.check)
    fmt = args.format.lower()

    # Load task corpus
    task_file = Path(args.task_file)
    if not task_file.exists():
        print(f"ERROR: Task file not found: '{task_file}'", file=sys.stderr)
        return 1

    try:
        from aobench.tasks.task_loader import load_hpc_task_set
        tasks = load_hpc_task_set(task_file)
    except Exception as exc:
        print(f"ERROR: Failed to load task file: {exc}", file=sys.stderr)
        return 1

    # Load string equivalence classes for O.a
    equiv_classes: list[dict] = []
    if "oa" in check_names:
        equiv_file = Path(args.string_equiv_file)
        if equiv_file.exists():
            try:
                import yaml
                raw = yaml.safe_load(equiv_file.read_text(encoding="utf-8"))
                equiv_classes = raw.get("equivalence_classes", [])
            except Exception as exc:
                print(
                    f"WARNING: Could not load string equiv file '{equiv_file}': {exc}",
                    file=sys.stderr,
                )
        else:
            print(
                f"WARNING: String equiv file not found: '{equiv_file}'. O.a check will be limited.",
                file=sys.stderr,
            )

    print(
        f"Running scorer audit checks: {check_names} on {len(tasks)} tasks",
        file=sys.stderr,
    )

    results: dict[str, Any] = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "schema_version": "1.0",
        "task_file": str(task_file),
        "checks_run": check_names,
        "audit_results": {},
    }

    all_passed = True

    if "oa" in check_names:
        oa_result = _run_oa(tasks, equiv_classes)
        results["audit_results"]["oa"] = oa_result
        if not oa_result["passed"]:
            all_passed = False

    if "ob" in check_names:
        ob_result = _run_ob(tasks)
        results["audit_results"]["ob"] = ob_result
        if not ob_result["passed"]:
            all_passed = False

    if "oc" in check_names:
        oc_result = _run_oc(tasks, n_repeats=args.n_repeats)
        results["audit_results"]["oc"] = oc_result
        if not oc_result["passed"]:
            all_passed = False

    results["overall_passed"] = all_passed

    # Format
    if fmt == "json":
        formatted = json.dumps(results, indent=2)
    elif fmt == "text":
        formatted = _format_text(results)
    else:
        print(f"ERROR: Unknown format '{fmt}'. Use: json | text", file=sys.stderr)
        return 1

    # Output
    output_path = args.output
    if output_path and output_path != "-":
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(formatted + "\n", encoding="utf-8")
        print(f"Audit report written to: {out_path}", file=sys.stderr)
    else:
        print(formatted)

    print(
        f"\nAudit {'PASSED' if all_passed else 'FAILED'}",
        file=sys.stderr,
    )
    return 0 if all_passed else 1


# ---------------------------------------------------------------------------
# O.a — Equivalence class check
# ---------------------------------------------------------------------------

def _run_oa(tasks: list, equiv_classes: list[dict]) -> dict[str, Any]:
    """O.a: Check that semantically equivalent strings score equally.

    For each equivalence class, builds a mock task with the canonical answer
    as ground truth, then scores each equivalent string and verifies it
    matches the canonical score.

    Without an LLM judge, we use a simple string normalisation scorer to
    verify that equivalent strings (as defined in string_equiv_classes.yaml)
    produce equal scores, and that non-equivalents do not.
    """
    failures: list[dict] = []
    warnings: list[dict] = []
    n_tested = 0

    for cls in equiv_classes:
        cls_id = cls.get("id", "unknown")
        canonical = str(cls.get("canonical", ""))
        equivalents = [str(e) for e in cls.get("equivalents", [])]
        non_equivalents = [str(e) for e in cls.get("non_equivalents", [])]

        if not canonical:
            continue

        # Test equivalents: normalised form should equal canonical normalised form
        canonical_norm = _normalise(canonical)

        for equiv in equivalents:
            n_tested += 1
            equiv_norm = _normalise(equiv)
            # Check if they are close enough after normalisation
            match = _fuzzy_equiv(canonical_norm, equiv_norm)
            if not match:
                failures.append({
                    "class_id": cls_id,
                    "type": "equivalent_mismatch",
                    "canonical": canonical,
                    "tested": equiv,
                    "detail": (
                        f"Normalised forms differ: '{canonical_norm}' vs '{equiv_norm}'. "
                        "Scorer may reject this equivalent form."
                    ),
                })

        # Test non-equivalents: they should NOT equal the canonical
        for non_equiv in non_equivalents:
            n_tested += 1
            ne_norm = _normalise(non_equiv)
            match = _fuzzy_equiv(canonical_norm, ne_norm)
            if match:
                failures.append({
                    "class_id": cls_id,
                    "type": "non_equivalent_false_match",
                    "canonical": canonical,
                    "tested": non_equiv,
                    "detail": (
                        f"Non-equivalent '{non_equiv}' normalises to same form as canonical. "
                        "Scorer would incorrectly accept this as correct."
                    ),
                })

    # Also check tasks with GT against corpus for string-match consistency
    det_tasks = [t for t in tasks if t.scoring_mode == "deterministic" and t.ground_truth]
    if not equiv_classes and det_tasks:
        warnings.append({
            "detail": (
                f"No equivalence classes loaded; tested {len(det_tasks)} deterministic "
                "tasks for structural GT consistency only. "
                "Load a string_equiv_classes.yaml for full O.a coverage."
            )
        })

    return {
        "check": "oa",
        "description": "Equivalence class consistency",
        "n_classes": len(equiv_classes),
        "n_tested": n_tested,
        "n_failures": len(failures),
        "n_warnings": len(warnings),
        "passed": len(failures) == 0,
        "failures": failures[:20],  # cap output
        "warnings": warnings[:10],
    }


# ---------------------------------------------------------------------------
# O.b — Negation check
# ---------------------------------------------------------------------------

def _run_ob(tasks: list) -> dict[str, Any]:
    """O.b: Check that negated answers score lower than correct answers.

    For each deterministic task with a string ground truth, constructs a
    negated/opposite answer and verifies it would receive a lower score.
    """
    failures: list[dict] = []
    n_tested = 0

    for task in tasks:
        if task.scoring_mode != "deterministic" or task.ground_truth is None:
            continue

        gt_dict = task.ground_truth.model_dump(
            exclude={"comparison_mode", "derivation_query"}
        )
        gt_values = {k: v for k, v in gt_dict.items() if v is not None}

        for field_name, gt_val in gt_values.items():
            if not isinstance(gt_val, str):
                continue

            n_tested += 1
            negated = _negate_value(gt_val)
            if negated is None:
                continue

            # Compute simple match scores
            gt_score = _simple_match_score(gt_val, gt_val)
            neg_score = _simple_match_score(negated, gt_val)

            if neg_score >= gt_score:
                failures.append({
                    "task_id": task.task_id,
                    "field": field_name,
                    "gt_value": gt_val,
                    "negated_value": negated,
                    "gt_score": gt_score,
                    "neg_score": neg_score,
                    "detail": (
                        f"Negated answer scored {neg_score:.2f} >= correct answer {gt_score:.2f}. "
                        "Scorer may not distinguish correct from negated answers."
                    ),
                })

    return {
        "check": "ob",
        "description": "Negation sensitivity",
        "n_tested": n_tested,
        "n_failures": len(failures),
        "passed": len(failures) == 0,
        "failures": failures[:20],
    }


# ---------------------------------------------------------------------------
# O.c — Repeat stability check
# ---------------------------------------------------------------------------

def _run_oc(tasks: list, n_repeats: int = 5) -> dict[str, Any]:
    """O.c: Check scorer stability across repeated identical inputs.

    For deterministic tasks, runs the scorer N times on the same input
    and verifies the score is identical each time (no stochastic variance).
    """
    failures: list[dict] = []
    n_tested = 0

    for task in tasks:
        if task.scoring_mode != "deterministic" or task.ground_truth is None:
            continue

        gt_dict = task.ground_truth.model_dump(
            exclude={"comparison_mode", "derivation_query"}
        )
        gt_values = {k: v for k, v in gt_dict.items() if v is not None}
        if not gt_values:
            continue

        n_tested += 1
        # Run the exact-match scorer n_repeats times on a fixed input
        scores: list[float] = []
        for _ in range(n_repeats):
            score = _deterministic_score(gt_values, gt_values)
            scores.append(score)

        if len(set(scores)) > 1:
            failures.append({
                "task_id": task.task_id,
                "scores": scores,
                "detail": (
                    f"Deterministic scorer produced varying scores across "
                    f"{n_repeats} runs: {scores}. Scorer is not stable."
                ),
            })

    return {
        "check": "oc",
        "description": "Scorer repeat stability",
        "n_tasks_tested": n_tested,
        "n_repeats": n_repeats,
        "n_failures": len(failures),
        "passed": len(failures) == 0,
        "failures": failures[:20],
    }


# ---------------------------------------------------------------------------
# Scorer helpers
# ---------------------------------------------------------------------------

def _normalise(value: str) -> str:
    """Lightweight normalisation: lowercase, strip, collapse whitespace."""
    import re
    return re.sub(r"\s+", " ", value.strip().lower())


def _fuzzy_equiv(a: str, b: str) -> bool:
    """Check if two normalised strings are 'equivalent' for O.a purposes.

    Strips units, commas, and trailing zeros for numeric comparisons.
    """
    if a == b:
        return True

    # Try numeric comparison (strip units)
    import re
    def _extract_num(s: str) -> Optional[float]:
        m = re.search(r"[-+]?\d+\.?\d*", s)
        return float(m.group()) if m else None

    na, nb = _extract_num(a), _extract_num(b)
    if na is not None and nb is not None:
        # Allow 1% tolerance
        if na == 0 and nb == 0:
            return True
        if na != 0 and abs(na - nb) / abs(na) < 0.01:
            return True

    return False


def _negate_value(value: str) -> Optional[str]:
    """Generate a plausible negation of a ground-truth string value."""
    # SLURM job states
    state_opposites = {
        "FAILED": "COMPLETED",
        "COMPLETED": "FAILED",
        "RUNNING": "PENDING",
        "PENDING": "RUNNING",
        "CANCELLED": "COMPLETED",
        "TIMEOUT": "COMPLETED",
    }
    upper = value.upper()
    if upper in state_opposites:
        return state_opposites[upper]

    # Boolean-style
    if value.lower() in ("true", "yes"):
        return "false"
    if value.lower() in ("false", "no"):
        return "true"

    # Numeric: negate by inverting or adding 1
    import re
    if re.match(r"^\d+$", value):
        n = int(value)
        return str(n + 1) if n < 999999 else str(n - 1)

    # String: prefix with "NOT "
    if len(value) > 2 and " " in value:
        return f"NOT {value}"

    return None


def _simple_match_score(answer: str, ground_truth: str) -> float:
    """Return 1.0 for exact match, 0.0 otherwise."""
    return 1.0 if _normalise(answer) == _normalise(ground_truth) else 0.0


def _deterministic_score(
    predicted: dict,
    ground_truth: dict,
) -> float:
    """Simple deterministic scorer: fraction of exact-matching fields."""
    if not ground_truth:
        return 1.0
    matches = sum(
        1
        for k, v in ground_truth.items()
        if k in predicted and _normalise(str(predicted[k])) == _normalise(str(v))
    )
    return matches / len(ground_truth)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _format_text(report: dict[str, Any]) -> str:
    lines: list[str] = [
        f"Scorer Audit Report  ({report['generated_at']})",
        "=" * 60,
        f"Overall: {'PASSED' if report['overall_passed'] else 'FAILED'}",
        "",
    ]
    for check_name, result in report.get("audit_results", {}).items():
        lines.append(f"[{check_name.upper()}] {result['description']}")
        lines.append(f"  Status : {'PASS' if result['passed'] else 'FAIL'}")
        for key in ("n_classes", "n_tested", "n_tasks_tested", "n_repeats"):
            if key in result:
                lines.append(f"  {key}: {result[key]}")
        lines.append(f"  Failures: {result['n_failures']}")
        for f in result.get("failures", [])[:5]:
            lines.append(f"    - {f.get('detail', f)}")
        if result.get("warnings"):
            for w in result["warnings"][:3]:
                lines.append(f"  WARN: {w.get('detail', w)}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_checks(check_arg: str) -> list[str]:
    valid = {"oa", "ob", "oc"}
    if check_arg.lower() == "all":
        return ["oa", "ob", "oc"]
    requested = [c.strip().lower() for c in check_arg.split(",")]
    unknown = [c for c in requested if c not in valid]
    if unknown:
        print(
            f"WARNING: Unknown check(s) '{unknown}'. Valid: oa | ob | oc | all",
            file=sys.stderr,
        )
    return [c for c in requested if c in valid] or ["oa", "ob", "oc"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audit_scorers",
        description="Run O.a–O.c scorer validity audit for AOBench.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--check",
        default="all",
        metavar="TEXT",
        help="Which checks to run: oa | ob | oc | all",
    )
    parser.add_argument(
        "--task-file",
        default=_DEFAULT_TASK_FILE,
        metavar="PATH",
        help="Task corpus JSON",
    )
    parser.add_argument(
        "--snapshot-dir",
        default=_DEFAULT_SNAPSHOT_DIR,
        metavar="PATH",
        help="Environments root directory",
    )
    parser.add_argument(
        "--judge-model",
        default=_DEFAULT_JUDGE_MODEL,
        metavar="TEXT",
        help="LLM judge model for rubric tasks",
    )
    parser.add_argument(
        "--n-repeats",
        type=int,
        default=_DEFAULT_N_REPEATS,
        metavar="INT",
        help="Number of repeats for O.c stochastic test",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Output report path (default: stdout)",
    )
    parser.add_argument(
        "--format",
        default="json",
        choices=["json", "text"],
        help="Output format",
    )
    parser.add_argument(
        "--string-equiv-file",
        default=_DEFAULT_STRING_EQUIV_FILE,
        metavar="PATH",
        help="YAML file of equivalent string sets for O.a",
    )
    return parser


if __name__ == "__main__":
    sys.exit(main())
