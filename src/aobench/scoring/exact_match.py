"""HPC quasi-exact match scorer — adapted from GAIA (Mialon et al. 2023).

Implements six normalization rules for HPC answer types:
  N1 — Job IDs: strip leading zeros, compare as integers
  N2 — Node lists: SLURM bracket expansion then set comparison
  N3 — Energy values: ±5% relative tolerance
  N4 — Partition names: case-insensitive exact match
  N5 — Generic strings: GAIA normalisation (articles, punctuation)
  N6 — Float answers: round to 2 decimal places (or ±5% if tolerance_pct set)

Source: Mialon et al. (2023), GAIA: a benchmark for General AI Assistants,
        arXiv:2311.12983.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def strip_leading_zeros(s: str) -> str:
    """Strip leading zeros from a numeric string. '00987654' → '987654'."""
    s = s.strip()
    if not s:
        return s
    # Handle negative sign
    negative = s.startswith("-")
    digits = s.lstrip("-").lstrip("0")
    if not digits:
        digits = "0"
    return ("-" + digits) if negative else digits


def parse_float(answer: str) -> float:
    """Strip HPC unit suffixes (kWh, MWh, GWh, kW, MW, W, %) and parse as float.

    Raises ValueError if no numeric value found.
    """
    s = answer.strip()
    # Remove unit suffixes (case-insensitive), longest match first
    suffixes = ["gwh", "mwh", "kwh", "mw", "kw", "w", "%"]
    lower = s.lower()
    for suffix in suffixes:
        if lower.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Cannot parse float from: {answer!r}")


def _remove_articles(s: str) -> str:
    """Remove leading articles 'a ', 'an ', 'the ' (case-insensitive)."""
    return re.sub(r"^(a |an |the )", "", s, flags=re.IGNORECASE)


def _remove_trailing_punctuation(s: str) -> str:
    """Remove trailing punctuation characters."""
    return s.rstrip(".,;:!?")


def expand_slurm_nodelist(nodelist: str) -> set[str]:
    """Expand SLURM bracket notation to a set of individual node names.

    Examples:
        expand_slurm_nodelist("node[01-04]")        == {"node01","node02","node03","node04"}
        expand_slurm_nodelist("node[01,03]")         == {"node01","node03"}
        expand_slurm_nodelist("node01,node02")       == {"node01","node02"}
        expand_slurm_nodelist("node042")             == {"node042"}
        expand_slurm_nodelist("node[01-02],gpu[01-02]") == {"node01","node02","gpu01","gpu02"}
        expand_slurm_nodelist("node[001-003]")       == {"node001","node002","node003"}
    """
    nodelist = nodelist.strip()
    if not nodelist:
        return set()

    # If no brackets at all, treat as comma-separated bare node names
    if "[" not in nodelist:
        return {n.strip() for n in nodelist.split(",") if n.strip()}

    result: set[str] = set()
    # Split top-level on commas that are NOT inside brackets
    # We process character by character to find top-level commas
    depth = 0
    segments: list[str] = []
    current: list[str] = []
    for ch in nodelist:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            segments.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        segments.append("".join(current))

    bracket_pattern = re.compile(r"^([a-zA-Z][a-zA-Z0-9_\-]*)(\[.*?\])$")

    for segment in segments:
        segment = segment.strip()
        m = bracket_pattern.match(segment)
        if not m:
            # bare node name
            if segment:
                result.add(segment)
            continue

        prefix = m.group(1)
        bracket_content = m.group(2)[1:-1]  # strip [ and ]

        # Split bracket content on commas
        for token in bracket_content.split(","):
            token = token.strip()
            if "-" in token:
                # Range token like "01-04" or "001-003"
                parts = token.split("-", 1)
                start_str, end_str = parts[0], parts[1]
                width = len(start_str)  # preserve leading-zero width
                try:
                    start = int(start_str)
                    end = int(end_str)
                except ValueError:
                    result.add(f"{prefix}{token}")
                    continue
                for i in range(start, end + 1):
                    result.add(f"{prefix}{str(i).zfill(width)}")
            else:
                result.add(f"{prefix}{token}")

    return result


# ---------------------------------------------------------------------------
# Normalization rules
# ---------------------------------------------------------------------------


def _normalize_job_id(answer: str) -> int:
    """N1: strip leading zeros and parse as integer."""
    s = answer.strip()
    # Handle scientific notation
    try:
        val = int(float(s))
        return val
    except ValueError:
        pass
    s = strip_leading_zeros(s)
    try:
        return int(s)
    except ValueError:
        raise ValueError(f"Cannot parse job_id from: {answer!r}")


def _normalize_energy(answer: str, tolerance_pct: float = 5.0) -> float:
    """N3: strip energy unit suffixes and parse as float."""
    return parse_float(answer)


def _normalize_partition(answer: str) -> str:
    """N4: case-insensitive exact match."""
    return answer.strip().lower()


def _normalize_string(answer: str) -> str:
    """N5: GAIA string normalisation."""
    s = answer.strip().lower()
    s = _remove_articles(s)
    s = _remove_trailing_punctuation(s)
    return s


def _normalize_float(answer: str) -> float:
    """N6: parse float, used for rounding comparison."""
    return parse_float(answer)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_answer(
    answer: str,
    answer_type: str,
    tolerance_pct: float = 5.0,
) -> str | int | float | set[str]:
    """Dispatch to the correct HPC normalization rule and return a normalised value."""
    if answer_type in ("job_id", "integer"):
        return _normalize_job_id(answer)
    elif answer_type == "node_list":
        return expand_slurm_nodelist(answer)
    elif answer_type in ("energy_kwh", "power_kw"):
        return _normalize_energy(answer, tolerance_pct)
    elif answer_type == "partition":
        # Handle comma-separated partition lists
        if "," in answer:
            return frozenset(_normalize_partition(p) for p in answer.split(","))
        return _normalize_partition(answer)
    elif answer_type == "float":
        return _normalize_float(answer)
    elif answer_type in ("string", "factoid"):
        return _normalize_string(answer)
    else:
        # Default: GAIA string normalisation
        return _normalize_string(answer)


def match_answers(
    candidate: str,
    ground_truth: str,
    answer_type: str,
    tolerance_pct: float = 5.0,
) -> bool:
    """Return True if candidate matches ground_truth under the rule for answer_type."""
    try:
        if answer_type in ("job_id", "integer"):
            try:
                c_val = _normalize_job_id(candidate)
                gt_val = _normalize_job_id(ground_truth)
            except ValueError:
                return False
            return c_val == gt_val

        elif answer_type == "node_list":
            c_set = expand_slurm_nodelist(candidate)
            gt_set = expand_slurm_nodelist(ground_truth)
            return c_set == gt_set

        elif answer_type in ("energy_kwh", "power_kw"):
            try:
                c_val = parse_float(candidate)
                gt_val = parse_float(ground_truth)
            except ValueError:
                return False
            if gt_val == 0.0:
                return c_val == 0.0
            relative_error = abs(c_val - gt_val) / abs(gt_val)
            return relative_error <= (tolerance_pct / 100.0)

        elif answer_type == "partition":
            if "," in candidate or "," in ground_truth:
                c_parts = frozenset(
                    _normalize_partition(p) for p in candidate.split(",")
                )
                gt_parts = frozenset(
                    _normalize_partition(p) for p in ground_truth.split(",")
                )
                return c_parts == gt_parts
            return _normalize_partition(candidate) == _normalize_partition(ground_truth)

        elif answer_type == "float":
            try:
                c_val = parse_float(candidate)
                gt_val = parse_float(ground_truth)
            except ValueError:
                return False
            if tolerance_pct != 5.0:
                # Use tolerance_pct if explicitly set (not default)
                if gt_val == 0.0:
                    return c_val == 0.0
                return abs(c_val - gt_val) / abs(gt_val) <= (tolerance_pct / 100.0)
            return round(c_val, 2) == round(gt_val, 2)

        elif answer_type in ("string", "factoid"):
            return _normalize_string(candidate) == _normalize_string(ground_truth)

        else:
            # Default: GAIA string normalisation
            return _normalize_string(candidate) == _normalize_string(ground_truth)

    except Exception:
        return False
