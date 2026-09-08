"""Guard: every surface that enumerates scored dimensions must cover all of them.

AOBench scores seven weighted dimensions. Several modules used to hard-code their
own six-item list, silently dropping ``workflow`` — which carries 0.10 weight in
``default_hpc_v01``. The run summary, the OTel export and ``compare runs`` each
under-reported the score surface as a result. These tests fail if a new dimension
is added to :class:`DimensionScores` and any consumer is not updated with it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from aobench.cli.compare_cmd import _DIMS
from aobench.exporters.otel.converter import _DIMENSIONS
from aobench.schemas.result import DIMENSION_NAMES, DimensionScores

PROFILES = Path(__file__).parent.parent.parent / "benchmark" / "configs" / "scoring_profiles.yaml"


def test_dimension_names_matches_the_schema():
    assert set(DIMENSION_NAMES) == set(DimensionScores.model_fields)
    assert len(DIMENSION_NAMES) == 7, "AOBench scores seven weighted dimensions"


def test_otel_exporter_covers_every_dimension():
    assert set(_DIMENSIONS) == set(DIMENSION_NAMES)


def test_compare_command_diffs_every_dimension():
    assert set(DIMENSION_NAMES) <= set(_DIMS)


def test_every_scoring_profile_weights_every_dimension():
    """A profile that omits a dimension silently drops it from the weighted sum."""
    profiles = yaml.safe_load(PROFILES.read_text(encoding="utf-8"))["profiles"]
    for name, body in profiles.items():
        weights = body.get("weights", {})
        missing = set(DIMENSION_NAMES) - set(weights)
        assert not missing, f"profile {name!r} does not weight: {sorted(missing)}"
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f"profile {name!r} weights sum to {total}, not 1.0"
