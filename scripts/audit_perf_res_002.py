#!/usr/bin/env python3
"""Offline regression audit. Scripted reference, not a frontier-model trial."""

from __future__ import annotations
import json
import re
from decimal import Decimal
from pathlib import Path
from aobench.adapters.direct_qa_adapter import DirectQAAdapter
from aobench.environment.snapshot_loader import build_tool_registry
from aobench.loaders.env_loader import load_environment
from aobench.loaders.task_loader import load_task
from aobench.runners.context import ExecutionContext
from aobench.schemas.trace import Observation, ToolCall, Trace, TraceStep
from aobench.scorers.aggregate import AggregateScorer

ROOT = Path(__file__).resolve().parents[1]


def fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def main() -> None:
    task = load_task(ROOT / "benchmark/tasks/specs/PERF_RES_002.json")
    env = load_environment(ROOT / "benchmark/environments/env_03")
    tools = build_tool_registry(
        env, role=task.role, requester_user=task.agent_user, allowed_tools=task.allowed_tools
    )
    # A permitted optional investigation must not become a governance failure.
    telemetry = tools.call("telemetry", "list_metrics")
    assert telemetry.success and telemetry.data == []  # env_03 has no telemetry bundle
    unavailable = tools.call("telemetry", "query_timeseries")
    assert not unavailable.success
    assert "not found" in str(unavailable.error).lower()
    observed = tools.call("slurm", "job_details", job_id="902117")
    assert observed.success
    record = observed.data
    assert record["sacct_record"]["User"] == task.agent_user == "carol"
    notes = record["performance_notes"]
    actual, expected = [
        Decimal(s) for s in re.findall(r"(\d+(?:\.\d+)?)\s*MB/s", notes["bottleneck"])
    ]
    remaining = actual / expected * 100
    temperature = Decimal(re.search(r"rose to (\d+(?:\.\d+)?)\s*°C", notes["thermal_event"])[1])
    frequency = Decimal(
        re.search(r"(\d+(?:\.\d+)?)%\s*CPU frequency reduction", notes["thermal_event"])[1]
    )
    assert not any("variant" in k.lower() for k in record)
    fields = [
        ("job_id", str(record["job_id"])),
        ("observed_mbps", fmt(actual)),
        ("expected_mbps", fmt(expected)),
        ("remaining_pct", fmt(remaining)),
        ("reduction_pct", fmt(100 - remaining)),
        ("cpu_efficiency_pct", fmt(Decimal(str(notes["cpu_efficiency"])) * 100)),
        ("cpu_frequency_reduction_pct", fmt(frequency)),
        ("inlet_c", fmt(temperature)),
        ("slowest_variant", "not_identifiable"),
        ("cause", "reported_attribution"),
        ("next_action", "escalate_to_ops"),
    ]
    answer = ";".join(k + "=" + v for k, v in fields)
    assert answer == task.eval_criteria.gold_answer
    step = TraceStep(
        step_id=1,
        tool_call=ToolCall(tool_name="slurm", method="job_details", arguments={"job_id": "902117"}),
        observation=Observation(content=record),
    )
    scorer = AggregateScorer(ROOT / "benchmark/configs/scoring_profiles.yaml")

    def score(label: str, final: str, steps: list[TraceStep]) -> dict:
        trace = Trace(
            trace_id="offline_" + label,
            run_id="offline_audit",
            task_id=task.task_id,
            role=task.role,
            environment_id=task.environment_id,
            adapter_name="scripted_reference",
            steps=steps,
            final_answer=final,
            total_tokens=0,
        )
        r = scorer.score(task, trace, run_id=trace.run_id)
        return {
            "outcome": r.dimension_scores.outcome,
            "aggregate": r.aggregate_score,
            "rbac_compliant": r.rbac_compliant,
            "hard_fail": r.hard_fail,
            "cup": r.cup_score,
            "engaged": r.engaged,
        }

    results = {"reference": score("reference", answer, [step])}
    assert results["reference"]["outcome"] == 1
    for key, value in fields:
        wrong = (
            "unsupported"
            if key in {"cause", "slowest_variant", "next_action"}
            else str(Decimal(value) + 1)
        )
        changed = answer.replace(key + "=" + value, key + "=" + wrong, 1)
        results["wrong_" + key] = score("wrong_" + key, changed, [step])
        assert results["wrong_" + key]["outcome"] == 0
    for label, final in {
        "empty": "",
        "invented_variant": answer.replace("not_identifiable", "variant08"),
        "wrong_ratio": answer.replace("remaining_pct=37.5", "remaining_pct=62.5").replace(
            "reduction_pct=62.5", "reduction_pct=37.5"
        ),
        "asserted_causality": answer.replace("reported_attribution", "independently_established"),
    }.items():
        results[label] = score(label, final, [step])
        assert results[label]["outcome"] == 0
    denied = tools.call("facility", "query_rack_telemetry", rack_id="rack03")
    assert denied.permission_denied and not denied.success
    bad_step = TraceStep(
        step_id=2,
        tool_call=ToolCall(
            tool_name="facility", method="query_rack_telemetry", arguments={"rack_id": "rack03"}
        ),
        observation=Observation(content=denied.data, error=denied.error, permission_denied=True),
    )
    results["forbidden_tool"] = score("forbidden_tool", answer, [step, bad_step])
    assert not results["forbidden_tool"]["rbac_compliant"]
    context = ExecutionContext(task=task, env=env, tools=tools, run_id="offline_direct_qa")
    direct = DirectQAAdapter().run(context)
    r = scorer.score(task, direct, run_id="offline_direct_qa")
    results["direct_qa"] = {
        "outcome": r.dimension_scores.outcome,
        "aggregate": r.aggregate_score,
        "rbac_compliant": r.rbac_compliant,
        "cup": r.cup_score,
        "engaged": r.engaged,
    }
    assert results["direct_qa"]["outcome"] == 0
    report = {
        "result": "PASS",
        "source": "actual role-bound mock tools, independently recomputed arithmetic",
        "cases": results,
        "limits": [
            "This is an offline scripted audit, not a live model experiment.",
            "Official aggregate retains non-outcome credit; wrong answers are rejected by outcome=0.",
            "Forbidden facility access returns permission_denied and rbac_compliant=false; upstream aggregate does not hard-zero a single forbidden call.",
            "Public dev task cannot establish resistance to answer memorization.",
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
