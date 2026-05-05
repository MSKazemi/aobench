"""Unit tests for src/aobench/scoring/exact_match.py."""

import pytest

from aobench.scoring.exact_match import (
    expand_slurm_nodelist,
    match_answers,
    parse_float,
    strip_leading_zeros,
)


# ---------------------------------------------------------------------------
# expand_slurm_nodelist tests
# ---------------------------------------------------------------------------


def test_expand_range():
    assert expand_slurm_nodelist("node[01-04]") == {"node01", "node02", "node03", "node04"}


def test_expand_list():
    assert expand_slurm_nodelist("node[01,03,05]") == {"node01", "node03", "node05"}


def test_expand_single():
    assert expand_slurm_nodelist("node042") == {"node042"}


def test_expand_comma_separated():
    assert expand_slurm_nodelist("node01,node02,node03") == {"node01", "node02", "node03"}


def test_expand_mixed_prefix():
    assert expand_slurm_nodelist("node[01-02],gpu[01-02]") == {
        "node01", "node02", "gpu01", "gpu02"
    }


def test_expand_zero_padding():
    assert expand_slurm_nodelist("node[001-003]") == {"node001", "node002", "node003"}


# ---------------------------------------------------------------------------
# match_answers tests — job_id (N1)
# ---------------------------------------------------------------------------


def test_job_id_leading_zeros():
    assert match_answers("00987654", "987654", "job_id") is True


def test_job_id_mismatch():
    assert match_answers("987655", "987654", "job_id") is False


def test_job_id_exact():
    assert match_answers("987654", "987654", "job_id") is True


# ---------------------------------------------------------------------------
# match_answers tests — node_list (N2)
# ---------------------------------------------------------------------------


def test_node_list_range_vs_expanded():
    assert match_answers("node[01-04]", "node01,node02,node03,node04", "node_list") is True


def test_node_list_order_insensitive():
    assert match_answers("node02,node01", "node01,node02", "node_list") is True


def test_node_list_mismatch():
    assert match_answers("node01,node02", "node01,node03", "node_list") is False


# ---------------------------------------------------------------------------
# match_answers tests — energy_kwh (N3)
# ---------------------------------------------------------------------------


def test_energy_within_tolerance():
    # 4190 vs 4200: relative error = 10/4200 ≈ 0.24% < 5%
    assert match_answers("4190 kWh", "4200", "energy_kwh") is True


def test_energy_outside_tolerance():
    # 3900 vs 4200: relative error = 300/4200 ≈ 7.1% > 5%
    assert match_answers("3900 kWh", "4200", "energy_kwh") is False


def test_energy_unit_stripping():
    # parse_float strips suffix but does NOT convert units;
    # "4.2 MWh" → 4.2, ground_truth "4200" → 4200 → mismatch
    assert match_answers("4.2 MWh", "4200", "energy_kwh") is False


def test_energy_exact():
    assert match_answers("4200 kWh", "4200", "energy_kwh") is True


# ---------------------------------------------------------------------------
# match_answers tests — partition (N4)
# ---------------------------------------------------------------------------


def test_partition_case_insensitive():
    assert match_answers("GPU", "gpu", "partition") is True


def test_partition_mismatch():
    assert match_answers("highmem", "gpu", "partition") is False


def test_partition_exact():
    assert match_answers("cpu", "cpu", "partition") is True


# ---------------------------------------------------------------------------
# match_answers tests — string (N5)
# ---------------------------------------------------------------------------


def test_string_gaia_normalisation():
    assert match_answers("The gpu partition.", "gpu partition", "string") is True


def test_string_article_removal():
    assert match_answers("a running job", "running job", "string") is True


def test_string_mismatch():
    assert match_answers("FAILED", "RUNNING", "string") is False


# ---------------------------------------------------------------------------
# parse_float tests
# ---------------------------------------------------------------------------


def test_parse_float_plain():
    assert parse_float("4200") == pytest.approx(4200.0)


def test_parse_float_kwh():
    assert parse_float("4200 kWh") == pytest.approx(4200.0)


def test_parse_float_mwh():
    assert parse_float("4.2 MWh") == pytest.approx(4.2)


def test_parse_float_percent():
    assert parse_float("94.3%") == pytest.approx(94.3)


def test_parse_float_invalid():
    with pytest.raises(ValueError):
        parse_float("N/A")


# ---------------------------------------------------------------------------
# strip_leading_zeros tests
# ---------------------------------------------------------------------------


def test_strip_leading_zeros_basic():
    assert strip_leading_zeros("00987654") == "987654"


def test_strip_leading_zeros_single_zero():
    assert strip_leading_zeros("0") == "0"


def test_strip_leading_zeros_no_zeros():
    assert strip_leading_zeros("987654") == "987654"
