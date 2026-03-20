"""Good-Same-Bad (GSB) comparative scorer.

Implements the GSB evaluation component from DAComp (Lei et al. 2025,
arXiv:2512.04324, §3.4).  The judge compares the agent response against a
set of pre-provided baseline answers on two axes:

- **Readability**         (4 sub-dimensions: clarity, structure, conciseness, formatting)
- **Analytical depth**    (4 sub-dimensions: rigor, domain relevance, insight, completeness)

For each baseline, the judge assigns a verdict:
  G (Good)  — agent response is better than this baseline
  S (Same)  — agent response is roughly equivalent
  B (Bad)   — agent response is worse than this baseline

The GSB score normalises the count of Good verdicts relative to the total:

    gsb_score = max(0, |G| − |B|) / (|G| + |S| + |B|)

This returns 0.0 when Bad ≥ Good, and approaches 1.0 as the agent response
consistently outperforms all baselines.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

LLMJudgeClient = Callable[[str], str]


_GSB_PROMPT_TEMPLATE = """\
You are an HPC domain expert evaluating AI assistant responses.

Compare the AGENT RESPONSE against the BASELINE RESPONSE below on two axes:

1. READABILITY  (consider: clarity, logical structure, appropriate conciseness, formatting)
2. ANALYTICAL DEPTH  (consider: technical rigor, domain relevance, insight quality, completeness)

For each axis assign one verdict:
  G = Agent response is clearly BETTER than the baseline
  S = Agent response is roughly the SAME quality as the baseline
  B = Agent response is clearly WORSE than the baseline

# Task Context
{task_context}

# Agent Response
{agent_response}

# Baseline Response #{baseline_index}
{baseline_response}

Return a JSON object with this exact structure:
{{
  "readability": {{
    "verdict": "<G|S|B>",
    "reason": "<one sentence>"
  }},
  "analytical_depth": {{
    "verdict": "<G|S|B>",
    "reason": "<one sentence>"
  }}
}}
"""


@dataclass
class GSBResult:
    score_gsb: float                  # [0, 1] — normalised GSB score
    good_count: int = 0               # total Good verdicts across all baselines × axes
    same_count: int = 0
    bad_count: int = 0
    per_baseline: list[dict[str, Any]] = field(default_factory=list)


def gsb_score(
    agent_output: str,
    baseline_answers: list[str],
    llm_client: LLMJudgeClient,
    *,
    task_context: str = "",
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> GSBResult:
    """Compute the Good-Same-Bad score for an agent response.

    Args:
        agent_output:      Agent's free-text response.
        baseline_answers:  Pre-annotated baseline answers (3–5 recommended).
        llm_client:        Callable ``(prompt: str) -> str`` for the judge LLM.
        task_context:      Optional HPC snapshot context for the judge.
        max_retries:       Retry attempts per baseline comparison.
        retry_delay:       Seconds between retries.

    Returns:
        GSBResult with normalised score and verdict counts.
    """
    if not baseline_answers:
        return GSBResult(score_gsb=0.0)

    total_g = total_s = total_b = 0
    per_baseline: list[dict[str, Any]] = []

    for idx, baseline in enumerate(baseline_answers, start=1):
        prompt = _GSB_PROMPT_TEMPLATE.format(
            task_context=task_context or "(No additional context)",
            agent_response=agent_output,
            baseline_response=baseline,
            baseline_index=idx,
        )

        parsed: dict[str, Any] | None = None
        last_err: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                raw = llm_client(prompt)
                parsed = _extract_json(raw)
                break
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "gsb_score baseline %d attempt %d/%d failed: %s",
                    idx, attempt, max_retries, exc,
                )
                if attempt < max_retries:
                    time.sleep(retry_delay)

        if parsed is None:
            logger.error("gsb_score: baseline %d failed after %d retries: %s", idx, max_retries, last_err)
            # Skip this baseline — do not penalise
            continue

        baseline_result: dict[str, Any] = {"baseline_index": idx, "axes": {}}
        for axis in ("readability", "analytical_depth"):
            axis_data = parsed.get(axis, {})
            verdict = str(axis_data.get("verdict", "S")).upper()
            reason = axis_data.get("reason", "")
            if verdict == "G":
                total_g += 1
            elif verdict == "B":
                total_b += 1
            else:
                total_s += 1
            baseline_result["axes"][axis] = {"verdict": verdict, "reason": reason}

        per_baseline.append(baseline_result)

    total = total_g + total_s + total_b
    if total == 0:
        return GSBResult(score_gsb=0.0, per_baseline=per_baseline)

    raw_score = max(0, total_g - total_b) / total
    return GSBResult(
        score_gsb=round(raw_score, 4),
        good_count=total_g,
        same_count=total_s,
        bad_count=total_b,
        per_baseline=per_baseline,
    )


def _extract_json(text: str) -> dict[str, Any]:
    stripped = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from GSB judge response:\n{text[:500]}")
