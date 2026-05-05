"""Judge configuration and config-ID generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class JudgeConfig:
    """Configuration for the LLM judge (rubric + taxonomy)."""

    model: str = "gpt-4o-2024-11-20"
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens_rubric: int = 1024
    max_tokens_taxonomy: int = 256
    seed_offset: int = 0
    # seed_offset is added to sha256(task_id) % 2**31 to derive per-task seeds.


def make_judge_config_id(
    config: JudgeConfig,
    rubric_text: str,
    taxonomy_text: str,
) -> str:
    """Return a 16-hex-character config ID derived from a SHA-256 hash.

    The hash covers: model, temperature, top_p, max_tokens_rubric,
    max_tokens_taxonomy, rubric prompt text, and taxonomy prompt text.
    seed_offset is intentionally excluded so that different random seeds
    share the same config ID (they represent the same judge configuration).

    Parameters
    ----------
    config:
        Judge configuration dataclass.
    rubric_text:
        Full text of the rubric prompt file (prompts/judge/rubric_v2.md).
    taxonomy_text:
        Full text of the taxonomy prompt file (prompts/judge/taxonomy_v2.md).

    Returns
    -------
    str
        First 16 hex characters of the SHA-256 digest (64-bit prefix).
    """
    blob = json.dumps(
        {
            "model": config.model,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens_rubric": config.max_tokens_rubric,
            "max_tokens_taxonomy": config.max_tokens_taxonomy,
            "rubric": rubric_text,
            "taxonomy": taxonomy_text,
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
