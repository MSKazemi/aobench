"""Unit tests for the hybrid scorer (deterministic + rubric paths)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from aobench.schemas.task import (
    ComponentSpec,
    HybridScoringConfig,
    TaskSpec,
)
from aobench.schemas.trace import Trace
from aobench.scorers.deterministic import deterministic_score
from aobench.scorers.gsb_scorer import gsb_score
from aobench.scorers.hybrid_scorer import HybridScorer
from aobench.scorers.rubric_scorer import load_rubric, rubric_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task(hybrid_scoring: HybridScoringConfig | None = None) -> TaskSpec:
    return TaskSpec(
        task_id="TEST_HYBRID_001",
        title="Hybrid scorer test",
        query_text="What is the energy consumption?",
        role="scientific_user",
        qcat="ENERGY",
        difficulty="easy",
        environment_id="env_test",
        expected_answer_type="numeric",
        hybrid_scoring=hybrid_scoring,
    )


def _trace(answer: str | None = None, hard_fail: bool = False) -> Trace:
    return Trace(
        trace_id="t1", run_id="r1", task_id="TEST_HYBRID_001",
        role="scientific_user", environment_id="env_test",
        adapter_name="direct_qa",
        final_answer=answer,
        hard_fail=hard_fail,
        hard_fail_reason="forced" if hard_fail else None,
    )


# ---------------------------------------------------------------------------
# deterministic_score unit tests
# ---------------------------------------------------------------------------

class TestDeterministicScore:
    def test_single_component_exact_numeric_match(self):
        specs = [ComponentSpec(
            component_id="energy_query",
            ground_truth={"energy_kwh": 4200},
            tolerance_pct=5.0,
            weight=1.0,
        )]
        agent_out = {"energy_query": {"energy_kwh": 4150}}  # 1.19% deviation — within 5%
        result = deterministic_score(agent_out, specs)
        assert result.sr == 1
        assert result.cs == 100.0
        assert result.cfs == 100.0
        assert result.outcome == 1.0

    def test_single_component_out_of_tolerance(self):
        specs = [ComponentSpec(
            component_id="energy_query",
            ground_truth={"energy_kwh": 4200},
            tolerance_pct=5.0,
            weight=1.0,
        )]
        agent_out = {"energy_query": {"energy_kwh": 3000}}  # 28% deviation — fail
        result = deterministic_score(agent_out, specs)
        assert result.sr == 0
        assert result.cs == 0.0
        assert result.cfs == 0.0
        assert result.outcome == 0.0

    def test_multi_component_partial_credit(self):
        specs = [
            ComponentSpec(component_id="a", ground_truth={"val": 10}, weight=1.0),
            ComponentSpec(component_id="b", ground_truth={"val": 20}, weight=1.0),
        ]
        # Only component 'a' matches
        agent_out = {"a": {"val": 10}, "b": {"val": 999}}
        result = deterministic_score(agent_out, specs)
        assert result.sr == 0
        assert result.cs == 50.0   # 1 of 2 correct
        assert result.outcome == 0.0

    def test_cascading_failure_propagation(self):
        """Correct child with wrong parent → CFS of child must be 0."""
        specs = [
            ComponentSpec(component_id="parent", ground_truth={"val": 1}, upstream_deps=[], weight=1.0),
            ComponentSpec(component_id="child",  ground_truth={"val": 2}, upstream_deps=["parent"], weight=1.0),
        ]
        # parent is WRONG, child is correct
        agent_out = {"parent": {"val": 999}, "child": {"val": 2}}
        result = deterministic_score(agent_out, specs)
        assert result.sr == 0
        # CS: child is correct → 50% isolated credit
        assert result.cs == 50.0
        # CFS: child inherits parent failure → 0%
        assert result.cfs == 0.0

    def test_all_correct_cascading(self):
        specs = [
            ComponentSpec(component_id="a", ground_truth={"val": 1}, upstream_deps=[], weight=1.0),
            ComponentSpec(component_id="b", ground_truth={"val": 2}, upstream_deps=["a"], weight=1.0),
        ]
        agent_out = {"a": {"val": 1}, "b": {"val": 2}}
        result = deterministic_score(agent_out, specs)
        assert result.sr == 1
        assert result.cs == 100.0
        assert result.cfs == 100.0

    def test_missing_component_output_scores_zero(self):
        specs = [ComponentSpec(component_id="energy", ground_truth={"val": 100}, weight=1.0)]
        result = deterministic_score({}, specs)  # empty agent output
        assert result.sr == 0
        assert result.cs == 0.0

    def test_no_components_returns_zero(self):
        result = deterministic_score({}, [])
        assert result.sr == 0
        assert result.cs == 0.0
        assert result.outcome == 0.0

    def test_weighted_cs(self):
        specs = [
            ComponentSpec(component_id="a", ground_truth={"val": 1}, weight=3.0),
            ComponentSpec(component_id="b", ground_truth={"val": 2}, weight=1.0),
        ]
        # Only 'a' is correct (weight 3); 'b' is wrong (weight 1)
        agent_out = {"a": {"val": 1}, "b": {"val": 999}}
        result = deterministic_score(agent_out, specs)
        # CS = 100 * 3 / (3+1) = 75.0
        assert result.cs == 75.0
        assert result.sr == 0

    def test_exact_match_type_string(self):
        specs = [ComponentSpec(
            component_id="partition",
            ground_truth={"name": "gpu"},
            match_type="exact",
            weight=1.0,
        )]
        assert deterministic_score({"partition": {"name": "gpu"}}, specs).sr == 1
        assert deterministic_score({"partition": {"name": "cpu"}}, specs).sr == 0

    def test_component_result_detail(self):
        specs = [ComponentSpec(
            component_id="energy",
            ground_truth={"energy_kwh": 4200},
            tolerance_pct=5.0,
        )]
        result = deterministic_score({"energy": {"energy_kwh": 4150}}, specs)
        assert len(result.component_results) == 1
        cr = result.component_results[0]
        assert cr.match is True
        assert cr.component_id == "energy"
        assert cr.deviation_pct is not None
        assert cr.deviation_pct < 5.0


# ---------------------------------------------------------------------------
# HybridScorer integration tests (deterministic path)
# ---------------------------------------------------------------------------

class TestHybridScorerDeterministic:
    scorer = HybridScorer()

    def _det_task(self, components: list[ComponentSpec]) -> TaskSpec:
        return _task(HybridScoringConfig(scoring_mode="deterministic", components=components))

    def test_hard_fail_returns_zero(self):
        task = self._det_task([ComponentSpec(component_id="a", ground_truth={"val": 1})])
        result = self.scorer.score(task, _trace(hard_fail=True))
        assert result.score == 0.0
        assert result.hard_fail is True

    def test_correct_deterministic_task(self):
        components = [ComponentSpec(component_id="node_count", ground_truth={"count": 32}, tolerance_pct=0)]
        task = self._det_task(components)
        trace = _trace(json.dumps({"node_count": {"count": 32}}))
        result = self.scorer.score(task, trace)
        assert result.score == 1.0

    def test_incorrect_deterministic_task(self):
        components = [ComponentSpec(component_id="node_count", ground_truth={"count": 32}, tolerance_pct=0)]
        task = self._det_task(components)
        trace = _trace(json.dumps({"node_count": {"count": 16}}))
        result = self.scorer.score(task, trace)
        assert result.score == 0.0

    def test_notes_contain_cs_cfs_sr(self):
        components = [ComponentSpec(component_id="a", ground_truth={"val": 5})]
        task = self._det_task(components)
        trace = _trace(json.dumps({"a": {"val": 5}}))
        result = self.scorer.score(task, trace)
        meta = json.loads(result.notes)
        assert "cs" in meta
        assert "cfs" in meta
        assert "sr" in meta
        assert meta["path"] == "deterministic"

    def test_no_hybrid_config_partial_credit(self):
        task = _task(hybrid_scoring=None)
        result = self.scorer.score(task, _trace("some answer"))
        assert result.score == 0.5

    def test_unknown_scoring_mode_raises(self):
        cfg = HybridScoringConfig.model_construct(
            scoring_mode="unknown",  # type: ignore[arg-type]
            components=[],
        )
        task = _task(hybrid_scoring=cfg)
        with pytest.raises(ValueError, match="Unknown scoring_mode"):
            self.scorer.score(task, _trace("x"))

    def test_non_json_final_answer_scores_zero(self):
        """Deterministic path needs JSON; plain text → empty output → zero."""
        components = [ComponentSpec(component_id="a", ground_truth={"val": 1})]
        task = self._det_task(components)
        trace = _trace("The answer is 42")  # plain text, not JSON
        result = self.scorer.score(task, trace)
        assert result.score == 0.0


# ---------------------------------------------------------------------------
# HybridScorer integration tests (rubric path)
# ---------------------------------------------------------------------------

_MOCK_JUDGE_RESPONSE = json.dumps({
    "dimensions": {
        "technical_correctness": {
            "path_chosen": "resource_exhaustion",
            "score": 3,
            "max_score": 3,
            "analysis": "Agent correctly identified OOM as cause.",
            "evidence": ["RSS 98%", "exit code 137"],
        },
        "role_appropriateness": {
            "path_chosen": None,
            "score": 2,
            "max_score": 2,
            "analysis": "Appropriate for sysadmin role.",
            "evidence": [],
        },
        "actionability": {
            "path_chosen": None,
            "score": 2,
            "max_score": 2,
            "analysis": "Clear remediation steps provided.",
            "evidence": [],
        },
    },
    "total_score": 7,
    "max_total": 7,
    "normalized_score": 1.0,
    "overall_rationale": "Excellent diagnosis with clear evidence and actionable steps.",
})


class TestHybridScorerRubric:
    def _rubric_task(self, baseline_answers: list[str] | None = None) -> TaskSpec:
        return _task(HybridScoringConfig(
            scoring_mode="rubric",
            rubric_id="hpc_job_failure_diagnosis_v1",
            task_context="Job 891234 failed at 14:32 UTC. MaxRSS=62G, limit=64G.",
            baseline_answers=baseline_answers or [],
            alpha=0.6,
        ))

    def test_rubric_no_llm_client_returns_zero_unscored(self):
        scorer = HybridScorer(llm_client=None)
        task = self._rubric_task()
        trace = _trace("The job failed due to OOM.")
        result = scorer.score(task, trace)
        assert result.score == 0.0
        assert "rubric_unscored" in (result.notes or "")

    def test_rubric_missing_rubric_id_returns_zero(self):
        cfg = HybridScoringConfig(scoring_mode="rubric", rubric_id=None)
        task = _task(hybrid_scoring=cfg)
        scorer = HybridScorer(llm_client=lambda p: _MOCK_JUDGE_RESPONSE)
        result = scorer.score(task, _trace("answer"))
        assert result.score == 0.0
        assert "rubric_id" in (result.notes or "")

    def test_rubric_empty_answer_returns_zero(self):
        scorer = HybridScorer(llm_client=lambda p: _MOCK_JUDGE_RESPONSE)
        task = self._rubric_task()
        result = scorer.score(task, _trace(""))
        assert result.score == 0.0

    def test_rubric_score_with_mock_judge(self):
        scorer = HybridScorer(llm_client=lambda p: _MOCK_JUDGE_RESPONSE)
        task = self._rubric_task()
        trace = _trace("The job failed due to OOM. RSS was at 98%. Exit code 137.")
        result = scorer.score(task, trace)
        # normalized_score=1.0, no baselines → alpha=1.0 → outcome=1.0
        assert result.score == 1.0

    def test_rubric_with_baselines_blends_gsb(self):
        _GSB_MOCK = json.dumps({
            "readability": {"verdict": "G", "reason": "Better than baseline."},
            "analytical_depth": {"verdict": "G", "reason": "More insightful."},
        })
        call_log: list[str] = []

        def _mock_judge(prompt: str) -> str:
            call_log.append(prompt)
            # Return GSB response for the second call onwards
            if len(call_log) == 1:
                return _MOCK_JUDGE_RESPONSE
            return _GSB_MOCK

        scorer = HybridScorer(llm_client=_mock_judge)
        task = self._rubric_task(baseline_answers=["Baseline answer 1"])
        trace = _trace("The job failed due to OOM. RSS was at 98%.")
        result = scorer.score(task, trace)

        # rubric=1.0, gsb=1.0 (2G,0S,0B → (2-0)/2=1.0), alpha=0.6
        # outcome = 0.6*1.0 + 0.4*1.0 = 1.0
        assert result.score == 1.0
        assert len(call_log) == 2  # one rubric + one GSB call

    def test_notes_contain_rubric_metadata(self):
        scorer = HybridScorer(llm_client=lambda p: _MOCK_JUDGE_RESPONSE)
        task = self._rubric_task()
        trace = _trace("The job failed due to OOM.")
        result = scorer.score(task, trace)
        meta = json.loads(result.notes)
        assert meta["path"] == "rubric"
        assert "score_rubric" in meta
        assert "breakdown" in meta
        assert "rationale" in meta


# ---------------------------------------------------------------------------
# GSB scorer unit tests
# ---------------------------------------------------------------------------

class TestGSBScore:
    def test_all_good_verdicts(self):
        mock_resp = json.dumps({
            "readability": {"verdict": "G", "reason": "Better"},
            "analytical_depth": {"verdict": "G", "reason": "More insightful"},
        })
        result = gsb_score("agent answer", ["baseline 1", "baseline 2"],
                           llm_client=lambda p: mock_resp)
        # 4 Good across 2 baselines × 2 axes = 4G, 0S, 0B → (4-0)/4 = 1.0
        assert result.score_gsb == 1.0
        assert result.good_count == 4

    def test_all_bad_verdicts(self):
        mock_resp = json.dumps({
            "readability": {"verdict": "B", "reason": "Worse"},
            "analytical_depth": {"verdict": "B", "reason": "Less insightful"},
        })
        result = gsb_score("agent answer", ["baseline 1"],
                           llm_client=lambda p: mock_resp)
        # max(0, 0-2)/2 = 0
        assert result.score_gsb == 0.0
        assert result.bad_count == 2

    def test_mixed_verdicts(self):
        # 1 baseline: readability=G, depth=S → 1G, 1S, 0B
        mock_resp = json.dumps({
            "readability": {"verdict": "G", "reason": "Better"},
            "analytical_depth": {"verdict": "S", "reason": "Same"},
        })
        result = gsb_score("agent answer", ["baseline"],
                           llm_client=lambda p: mock_resp)
        # (1-0)/(1+1+0) = 0.5
        assert result.score_gsb == 0.5

    def test_no_baselines_returns_zero(self):
        result = gsb_score("agent answer", [], llm_client=lambda p: "{}")
        assert result.score_gsb == 0.0


# ---------------------------------------------------------------------------
# Rubric loader tests
# ---------------------------------------------------------------------------

class TestRubricLoader:
    def test_load_builtin_rubrics(self):
        for rubric_id in [
            "hpc_job_failure_diagnosis_v1",
            "hpc_energy_anomaly_v1",
            "hpc_rbac_response_v1",
        ]:
            rubric = load_rubric(rubric_id)
            assert rubric["rubric_id"] == rubric_id
            assert "dimensions" in rubric

    def test_missing_rubric_raises(self):
        with pytest.raises(FileNotFoundError, match="not_a_real_rubric"):
            load_rubric("not_a_real_rubric")

    def test_rubric_has_required_fields(self):
        rubric = load_rubric("hpc_job_failure_diagnosis_v1")
        assert "rubric_id" in rubric
        assert "dimensions" in rubric
        assert len(rubric["dimensions"]) > 0
