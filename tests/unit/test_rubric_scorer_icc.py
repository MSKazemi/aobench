"""Unit tests for the ICC(A,1) reliability gate in rubric_scorer."""

from __future__ import annotations

import pytest

from exabench.scorers.rubric_scorer import (
    RubricReliabilityError,
    compute_icc,
    validate_rubric_reliability,
)


# ---------------------------------------------------------------------------
# compute_icc
# ---------------------------------------------------------------------------

class TestComputeICC:
    def test_high_agreement_near_one(self):
        """Near-identical per-judge scores should yield ICC close to 1."""
        # 3 judges × 5 dimensions, tiny jitter
        ratings = [
            [0.9, 0.8, 0.7, 0.6, 0.5],
            [0.91, 0.79, 0.71, 0.61, 0.49],
            [0.89, 0.81, 0.69, 0.59, 0.51],
        ]
        icc = compute_icc(ratings)
        assert icc > 0.90, f"Expected ICC > 0.90, got {icc:.4f}"

    def test_random_disagreement_low(self):
        """Judges who disagree randomly should yield low ICC."""
        import random
        rng = random.Random(42)
        ratings = [
            [rng.random() for _ in range(6)],
            [rng.random() for _ in range(6)],
            [rng.random() for _ in range(6)],
        ]
        icc = compute_icc(ratings)
        assert icc < 0.80, f"Expected ICC < 0.80 for random scores, got {icc:.4f}"

    def test_requires_at_least_two_judges(self):
        with pytest.raises(ValueError, match="at least 2 judges"):
            compute_icc([[0.5, 0.6, 0.7]])

    def test_requires_at_least_two_dimensions(self):
        with pytest.raises(ValueError, match="at least 2 dimensions"):
            compute_icc([[0.5], [0.6]])

    def test_returns_float(self):
        ratings = [
            [1.0, 0.8, 0.6],
            [0.9, 0.7, 0.5],
        ]
        result = compute_icc(ratings)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# validate_rubric_reliability
# ---------------------------------------------------------------------------

class TestValidateRubricReliability:
    def _high_agreement_ratings(self):
        return [
            [0.9, 0.8, 0.7, 0.6, 0.5],
            [0.91, 0.79, 0.71, 0.61, 0.49],
            [0.89, 0.81, 0.69, 0.59, 0.51],
        ]

    def _low_agreement_ratings(self):
        import random
        rng = random.Random(7)
        return [[rng.random() for _ in range(6)] for _ in range(3)]

    def test_passes_for_high_agreement(self):
        assert validate_rubric_reliability(self._high_agreement_ratings()) is True

    def test_fails_for_low_agreement(self):
        assert validate_rubric_reliability(self._low_agreement_ratings()) is False

    def test_custom_threshold_respected(self):
        # High-agreement ratings should pass at 0.80 but we can raise threshold to 0.99
        ratings = self._high_agreement_ratings()
        icc = compute_icc(ratings)
        above = icc + 0.005 if icc < 0.995 else 0.999
        assert validate_rubric_reliability(ratings, threshold=above) is False
        assert validate_rubric_reliability(ratings, threshold=icc - 0.005) is True


# ---------------------------------------------------------------------------
# rubric_score ICC gate integration (mocked judge)
# ---------------------------------------------------------------------------

class TestRubricScoreICCGate:
    """Test that rubric_score raises RubricReliabilityError when ICC < threshold."""

    def _make_judge_response(self, dim_scores: dict[str, float], normalized: float) -> str:
        import json
        dims = {
            name: {
                "path_chosen": None,
                "score": score,
                "max_score": 1.0,
                "analysis": "test",
                "evidence": [],
            }
            for name, score in dim_scores.items()
        }
        return json.dumps({
            "dimensions": dims,
            "total_score": sum(dim_scores.values()),
            "max_total": len(dim_scores),
            "normalized_score": normalized,
            "overall_rationale": "test rationale",
        })

    def test_single_judge_no_gate(self, tmp_path):
        """n_judges=1 should never trigger the ICC gate."""
        import json
        from pathlib import Path
        from exabench.scorers.rubric_scorer import rubric_score

        rubric_id = "test_icc_rubric"
        rubric = {
            "rubric_id": rubric_id,
            "dimensions": {
                "dim_a": {"max_score": 1},
                "dim_b": {"max_score": 1},
            },
        }
        rubric_file = tmp_path / f"{rubric_id}.yaml"
        import yaml
        rubric_file.write_text(yaml.dump(rubric))

        response = self._make_judge_response({"dim_a": 0.5, "dim_b": 0.5}, 0.5)
        client = lambda _prompt: response  # noqa: E731

        result = rubric_score(
            "agent response",
            rubric_id,
            "ctx",
            client,
            rubric_dir=tmp_path,
            n_judges=1,
        )
        assert 0.0 <= result.score_rubric <= 1.0

    def test_multi_judge_high_agreement_passes(self, tmp_path):
        """n_judges>=2 with agreeing judges should pass the ICC gate."""
        import yaml
        from exabench.scorers.rubric_scorer import rubric_score

        rubric_id = "test_icc_rubric2"
        rubric = {"rubric_id": rubric_id, "dimensions": {f"d{i}": {"max_score": 1} for i in range(5)}}
        (tmp_path / f"{rubric_id}.yaml").write_text(yaml.dump(rubric))

        # High ICC requires high between-dimension variance AND low within-dimension
        # variance.  Use a wide score spread across dimensions with tiny per-judge jitter.
        base_scores = [0.1, 0.3, 0.5, 0.8, 1.0]  # wide spread → high between-subject variance
        call_count = [0]

        def agreeing_judge(_prompt):
            call_count[0] += 1
            jitter = (call_count[0] - 1) * 0.002  # 0.000, 0.002, 0.004 per judge
            return self._make_judge_response(
                {f"d{i}": base_scores[i] + jitter for i in range(5)},
                sum(base_scores) / len(base_scores),
            )

        result = rubric_score(
            "agent response",
            rubric_id,
            "ctx",
            agreeing_judge,
            rubric_dir=tmp_path,
            n_judges=3,
        )
        assert 0.0 <= result.score_rubric <= 1.0

    def test_multi_judge_disagreement_raises(self, tmp_path):
        """n_judges>=2 with strongly disagreeing judges should raise RubricReliabilityError."""
        import random
        import yaml
        from exabench.scorers.rubric_scorer import rubric_score

        rubric_id = "test_icc_rubric3"
        rubric = {"rubric_id": rubric_id, "dimensions": {f"d{i}": {"max_score": 1} for i in range(6)}}
        (tmp_path / f"{rubric_id}.yaml").write_text(yaml.dump(rubric))

        rng = random.Random(99)
        call_count = [0]

        def random_judge(_prompt):
            call_count[0] += 1
            return self._make_judge_response(
                {f"d{i}": rng.random() for i in range(6)},
                rng.random(),
            )

        with pytest.raises(RubricReliabilityError, match="ICC"):
            rubric_score(
                "agent response",
                rubric_id,
                "ctx",
                random_judge,
                rubric_dir=tmp_path,
                n_judges=4,
                icc_threshold=0.80,
            )
