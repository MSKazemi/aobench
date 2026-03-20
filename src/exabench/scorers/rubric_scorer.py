"""Rubric scorer — LLM-judge with hierarchical rubric + path selection.

Implements the rubric evaluation path from the hybrid scorer spec (§4).
The judge receives the hierarchical rubric YAML, the agent response, and
HPC task context, then returns per-dimension scores and a rationale.

Evidence-first policy: if the agent makes a claim without citing data from
the HPC snapshot, the item scores 0.

LLM judge interface
-------------------
Pass any callable satisfying:

    (prompt: str) -> str

via the ``llm_client`` parameter.  Two convenience factories are provided:

    make_openai_judge(model="gpt-4.1")         # requires openai package
    make_anthropic_judge(model="claude-opus-4-6")  # requires anthropic package
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

logger = logging.getLogger(__name__)

# Type alias for the judge callable
LLMJudgeClient = Callable[[str], str]

# Default rubric directory (co-located with this module)
_RUBRIC_DIR = Path(__file__).parent / "rubrics"


# ---------------------------------------------------------------------------
# Rubric loading
# ---------------------------------------------------------------------------

def load_rubric(rubric_id: str, rubric_dir: Path | None = None) -> dict[str, Any]:
    """Load a rubric YAML by ID from the rubric directory."""
    search_dir = rubric_dir or _RUBRIC_DIR
    path = search_dir / f"{rubric_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Rubric '{rubric_id}' not found at {path}. "
            f"Available rubrics: {[p.stem for p in search_dir.glob('*.yaml')]}"
        )
    with path.open() as f:
        data = yaml.safe_load(f)
    if data.get("rubric_id") != rubric_id:
        raise ValueError(
            f"rubric_id mismatch: file declares '{data.get('rubric_id')}', expected '{rubric_id}'"
        )
    return data


# ---------------------------------------------------------------------------
# Judge prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert HPC systems evaluator. Your task is to score an AI agent's \
response to an HPC operations query using the provided hierarchical rubric.

EVIDENCE-FIRST POLICY: If the agent makes a factual claim but does not cite \
supporting evidence from the HPC snapshot or system data, assign 0 points \
for that item regardless of whether the claim happens to be correct.

Return your evaluation as a JSON object following the schema specified in \
the instructions. Do not include any text before or after the JSON object.\
"""

_JUDGE_PROMPT_TEMPLATE = """\
# Task Context
{task_context}

# Agent Response
{agent_response}

# Scoring Rubric
{rubric_yaml}

# Scoring Instructions

For each dimension in the rubric:

**If the dimension has `paths`:**
1. Identify the best-matching path based on the agent's approach.
2. Score only the items under that path.
3. If no path matches, use expert judgment capped at the maximum path score.

**If the dimension has `levels`:**
Score from the lowest level that the agent achieves. Each level is cumulative.

Return a JSON object with this structure:
{{
  "dimensions": {{
    "<dimension_name>": {{
      "path_chosen": "<path name or null>",
      "score": <numeric score>,
      "max_score": <max possible for this dimension>,
      "analysis": "<1-2 sentence rationale>",
      "evidence": ["<quoted evidence from agent response>"]
    }}
  }},
  "total_score": <sum of dimension scores>,
  "max_total": <sum of dimension max scores>,
  "normalized_score": <total_score / max_total, 0.0-1.0>,
  "overall_rationale": "<2-3 sentence overall assessment>"
}}
"""


def _build_prompt(
    agent_response: str,
    rubric: dict[str, Any],
    task_context: str,
) -> str:
    rubric_yaml = yaml.dump(rubric, default_flow_style=False, allow_unicode=True)
    return _JUDGE_PROMPT_TEMPLATE.format(
        task_context=task_context or "(No additional task context provided)",
        agent_response=agent_response,
        rubric_yaml=rubric_yaml,
    )


# ---------------------------------------------------------------------------
# Judge response parsing
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a (possibly markdown-wrapped) string."""
    # Strip markdown code fences if present
    stripped = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        # Try to find { ... } block
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from judge response:\n{text[:500]}")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RubricResult:
    score_rubric: float                          # normalised rubric score [0, 1]
    breakdown: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    raw_judge_output: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------

def rubric_score(
    agent_output: str,
    rubric_id: str,
    task_context: str,
    llm_client: LLMJudgeClient,
    *,
    rubric_dir: Path | None = None,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> RubricResult:
    """Run the LLM judge against a hierarchical rubric.

    Args:
        agent_output:  The agent's free-text response.
        rubric_id:     ID of the rubric YAML to load.
        task_context:  HPC snapshot summary injected into the judge prompt.
        llm_client:    Callable ``(prompt: str) -> str`` for the judge LLM.
        rubric_dir:    Override the default rubric search directory.
        max_retries:   Number of retry attempts on judge failure.
        retry_delay:   Seconds between retries.

    Returns:
        RubricResult with normalised score, per-dimension breakdown, and rationale.

    Raises:
        RuntimeError: If judge fails after all retries.
    """
    rubric = load_rubric(rubric_id, rubric_dir=rubric_dir)
    full_prompt = _SYSTEM_PROMPT + "\n\n" + _build_prompt(agent_output, rubric, task_context)

    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            raw_text = llm_client(full_prompt)
            parsed = _extract_json(raw_text)
            break
        except Exception as exc:
            last_err = exc
            logger.warning(
                "rubric_score judge attempt %d/%d failed: %s", attempt, max_retries, exc
            )
            if attempt < max_retries:
                time.sleep(retry_delay)
    else:
        raise RuntimeError(
            f"LLM judge failed after {max_retries} attempts: {last_err}"
        )

    normalized = float(parsed.get("normalized_score", 0.0))
    normalized = max(0.0, min(1.0, normalized))

    breakdown: dict[str, Any] = {}
    for dim_name, dim_data in parsed.get("dimensions", {}).items():
        breakdown[dim_name] = {
            "score": dim_data.get("score", 0),
            "max_score": dim_data.get("max_score", 0),
            "path_chosen": dim_data.get("path_chosen"),
            "analysis": dim_data.get("analysis", ""),
            "evidence": dim_data.get("evidence", []),
        }

    return RubricResult(
        score_rubric=normalized,
        breakdown=breakdown,
        rationale=parsed.get("overall_rationale", ""),
        raw_judge_output=parsed,
    )


# ---------------------------------------------------------------------------
# Convenience judge factories
# ---------------------------------------------------------------------------

def make_openai_judge(
    model: str = "gpt-4.1",
    api_key: str | None = None,
    **kwargs: Any,
) -> LLMJudgeClient:
    """Create an OpenAI-backed LLM judge client.

    Requires ``pip install openai``.
    """
    try:
        import openai  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "openai package required for make_openai_judge: pip install openai"
        ) from exc

    client = openai.OpenAI(api_key=api_key, **kwargs)

    def _call(prompt: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return resp.choices[0].message.content or ""

    return _call


def make_anthropic_judge(
    model: str = "claude-opus-4-6",
    api_key: str | None = None,
    **kwargs: Any,
) -> LLMJudgeClient:
    """Create an Anthropic-backed LLM judge client.

    Requires ``pip install anthropic``.
    """
    try:
        import anthropic  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "anthropic package required for make_anthropic_judge: pip install anthropic"
        ) from exc

    client = anthropic.Anthropic(api_key=api_key, **kwargs)

    def _call(prompt: str) -> str:
        msg = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text if msg.content else ""

    return _call
