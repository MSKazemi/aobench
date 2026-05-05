"""LLM judge runner — rubric scoring and error taxonomy annotation."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

from .config import JudgeConfig, make_judge_config_id

logger = logging.getLogger(__name__)

# Path to prompt files relative to this file's package root
_PROMPTS_DIR = Path(__file__).parents[4] / "prompts" / "judge"

# Retry configuration
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # seconds
_JITTER_TEMP = 0.3


def _load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts/judge/ directory."""
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Judge prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def _task_seed(task_id: str, seed_offset: int) -> int:
    """Derive a deterministic integer seed from task_id + seed_offset."""
    digest_int = int.from_bytes(
        hashlib.sha256(task_id.encode()).digest(), byteorder="big"
    )
    return (digest_int % (2**31)) + seed_offset


def _parse_json_response(text: str) -> Optional[dict]:
    """Attempt to parse JSON from an LLM response. Returns None on failure."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines if they are fences
        start = 1 if lines[0].startswith("```") else 0
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


class JudgeRunner:
    """Runs LLM-based rubric scoring and error taxonomy annotation.

    Uses OpenAI as the primary backend (imported lazily). Falls back to
    Anthropic claude-sonnet-4-6 if OpenAI is unavailable or fails.

    Parameters
    ----------
    config:
        Judge configuration. Defaults to JudgeConfig() if not provided.
    """

    def __init__(self, config: Optional[JudgeConfig] = None) -> None:
        self.config = config or JudgeConfig()
        self._rubric_text = _load_prompt("rubric_v2.md")
        self._taxonomy_text = _load_prompt("taxonomy_v2.md")
        self._config_id = make_judge_config_id(
            self.config, self._rubric_text, self._taxonomy_text
        )

    @property
    def config_id(self) -> str:
        """16-character hex config ID for this runner's config + prompts."""
        return self._config_id

    # ── Public API ────────────────────────────────────────────────────────────

    def score_rubric(
        self,
        task_id: str,
        query: str,
        response: str,
        role: str,
    ) -> dict:
        """Score an agent response on the rubric dimensions.

        Parameters
        ----------
        task_id:
            Task identifier (used for seed derivation).
        query:
            The task question / prompt given to the agent.
        response:
            The agent's response text.
        role:
            The agent's HPC role (e.g. "job_user", "sysadmin").

        Returns
        -------
        dict with keys:
            completeness, accuracy, grounding, safety (int 0-3),
            rationale (str), confidence (float),
            judge_score (float, normalised 0-1),
            judge_status ("ok" | "parse_error"),
            judge_retry_jitter (bool),
            judge_quality ("cloud" | "fallback"),
            judge_config_id (str),
            judge_input_tokens (int | None),
            judge_output_tokens (int | None),
            judge_cost_usd (float | None).
        """
        seed = _task_seed(task_id, self.config.seed_offset)
        user_content = self._build_rubric_user_message(query, response, role)
        system_content = self._extract_system(self._rubric_text)

        return self._call_with_retry(
            system_content=system_content,
            user_content=user_content,
            max_tokens=self.config.max_tokens_rubric,
            seed=seed,
            parse_fn=self._parse_rubric_response,
            call_type="rubric",
        )

    def annotate_taxonomy(
        self,
        task_id: str,
        trace_text: str,
    ) -> dict:
        """Annotate a trace with HPC error taxonomy categories.

        Parameters
        ----------
        task_id:
            Task identifier (used for seed derivation).
        trace_text:
            Full text of the execution trace.

        Returns
        -------
        dict with keys:
            errors (list[dict]),
            annotation_confidence (float),
            judge_status ("ok" | "parse_error"),
            judge_quality ("cloud" | "fallback"),
            judge_config_id (str),
            judge_input_tokens (int | None),
            judge_output_tokens (int | None),
            judge_cost_usd (float | None).
        """
        seed = _task_seed(task_id, self.config.seed_offset)
        user_content = self._build_taxonomy_user_message(trace_text)
        system_content = self._extract_system(self._taxonomy_text)

        return self._call_with_retry(
            system_content=system_content,
            user_content=user_content,
            max_tokens=self.config.max_tokens_taxonomy,
            seed=seed,
            parse_fn=self._parse_taxonomy_response,
            call_type="taxonomy",
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _call_with_retry(
        self,
        system_content: str,
        user_content: str,
        max_tokens: int,
        seed: int,
        parse_fn,
        call_type: str,
    ) -> dict:
        """Attempt the API call with retry logic.

        Retry policy:
          Attempt 1: temp=0.0
          Attempt 2 (parse failure): temp=0.0 retry
          Attempt 3 (still failing): temp=0.3 with jitter flag set
          HTTP 429/5xx: exponential backoff, 3 retries
        """
        jitter = False
        last_result = None

        for attempt in range(1, _MAX_RETRIES + 1):
            temperature = _JITTER_TEMP if attempt == 3 else self.config.temperature
            if attempt == 3:
                jitter = True

            result = self._try_openai(
                system_content=system_content,
                user_content=user_content,
                max_tokens=max_tokens,
                temperature=temperature,
                seed=seed,
                parse_fn=parse_fn,
                call_type=call_type,
            )

            if result is not None:
                result["judge_retry_jitter"] = jitter
                result["judge_config_id"] = self._config_id
                return result

            last_result = result  # None on parse failure

        # All OpenAI attempts failed — try Anthropic fallback
        fallback = self._try_anthropic(
            system_content=system_content,
            user_content=user_content,
            max_tokens=max_tokens,
            parse_fn=parse_fn,
            call_type=call_type,
        )
        if fallback is not None:
            fallback["judge_retry_jitter"] = jitter
            fallback["judge_config_id"] = self._config_id
            fallback["judge_quality"] = "fallback"
            return fallback

        # All attempts exhausted
        return self._error_result(call_type, jitter=jitter, status="parse_error")

    def _try_openai(
        self,
        system_content: str,
        user_content: str,
        max_tokens: int,
        temperature: float,
        seed: int,
        parse_fn,
        call_type: str,
    ) -> Optional[dict]:
        """Try to call the OpenAI API. Returns parsed result dict or None."""
        try:
            import openai  # noqa: PLC0415 — lazy import for optional dependency
        except ImportError:
            logger.debug("openai package not installed; skipping OpenAI judge")
            return None

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        backoff = _BACKOFF_BASE
        for http_attempt in range(_MAX_RETRIES):
            try:
                client = openai.OpenAI()
                resp = client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    top_p=self.config.top_p,
                    max_tokens=max_tokens,
                    seed=seed,
                )
                text = resp.choices[0].message.content or ""
                parsed = parse_fn(text)
                if parsed is None:
                    logger.warning(
                        "Judge parse failure (openai, %s, attempt %d)",
                        call_type,
                        http_attempt + 1,
                    )
                    return None  # Signal parse failure to retry outer loop

                parsed["judge_quality"] = "cloud"
                parsed["judge_status"] = "ok"
                parsed["judge_input_tokens"] = getattr(
                    resp.usage, "prompt_tokens", None
                )
                parsed["judge_output_tokens"] = getattr(
                    resp.usage, "completion_tokens", None
                )
                parsed["judge_cost_usd"] = None  # Caller may enrich later
                return parsed

            except openai.RateLimitError:
                logger.warning(
                    "OpenAI 429 rate limit on attempt %d; backing off %.1fs",
                    http_attempt + 1,
                    backoff,
                )
                time.sleep(backoff)
                backoff *= 2

            except openai.APIStatusError as exc:
                if exc.status_code and exc.status_code >= 500:
                    logger.warning(
                        "OpenAI 5xx (status=%s) on attempt %d; backing off %.1fs",
                        exc.status_code,
                        http_attempt + 1,
                        backoff,
                    )
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error("OpenAI API error: %s", exc)
                    return None

            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected OpenAI error: %s", exc)
                return None

        return None  # HTTP retries exhausted

    def _try_anthropic(
        self,
        system_content: str,
        user_content: str,
        max_tokens: int,
        parse_fn,
        call_type: str,
    ) -> Optional[dict]:
        """Try Anthropic claude-sonnet-4-6 as fallback judge."""
        try:
            import anthropic  # noqa: PLC0415 — lazy import
        except ImportError:
            logger.debug("anthropic package not installed; fallback unavailable")
            return None

        try:
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                system=system_content,
                messages=[{"role": "user", "content": user_content}],
                max_tokens=max_tokens,
                temperature=self.config.temperature,
            )
            text = resp.content[0].text if resp.content else ""
            parsed = parse_fn(text)
            if parsed is None:
                logger.warning(
                    "Judge parse failure (anthropic fallback, %s)", call_type
                )
                return None

            parsed["judge_quality"] = "fallback"
            parsed["judge_status"] = "ok"
            parsed["judge_input_tokens"] = getattr(resp.usage, "input_tokens", None)
            parsed["judge_output_tokens"] = getattr(resp.usage, "output_tokens", None)
            parsed["judge_cost_usd"] = None
            return parsed

        except Exception as exc:  # noqa: BLE001
            logger.error("Anthropic fallback error: %s", exc)
            return None

    # ── Message builders ──────────────────────────────────────────────────────

    def _build_rubric_user_message(
        self, query: str, response: str, role: str
    ) -> str:
        return (
            f"**Agent role**: {role}\n\n"
            f"**Task query**:\n{query}\n\n"
            f"**Agent response**:\n{response}\n\n"
            "Score the response on the four rubric dimensions and return JSON."
        )

    def _build_taxonomy_user_message(self, trace_text: str) -> str:
        return (
            f"**Execution trace**:\n{trace_text}\n\n"
            "Annotate all errors in the trace using the HPC error taxonomy "
            "and return JSON."
        )

    @staticmethod
    def _extract_system(prompt_text: str) -> str:
        """Extract the ## System section from a prompt markdown file."""
        lines = prompt_text.splitlines()
        in_system = False
        system_lines = []
        for line in lines:
            if line.strip() == "## System":
                in_system = True
                continue
            if in_system:
                if line.startswith("## "):
                    break
                system_lines.append(line)
        return "\n".join(system_lines).strip()

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_rubric_response(self, text: str) -> Optional[dict]:
        """Parse rubric JSON from LLM output. Returns None on failure."""
        data = _parse_json_response(text)
        if data is None:
            return None
        required = {"completeness", "accuracy", "grounding", "safety"}
        if not required.issubset(data.keys()):
            return None
        # Normalise score to [0, 1]
        total = sum(data.get(k, 0) for k in required)
        data["judge_score"] = round(total / 12.0, 4)  # max possible = 4*3 = 12
        return data

    def _parse_taxonomy_response(self, text: str) -> Optional[dict]:
        """Parse taxonomy JSON from LLM output. Returns None on failure."""
        data = _parse_json_response(text)
        if data is None:
            return None
        if "errors" not in data:
            return None
        return data

    # ── Error result factory ──────────────────────────────────────────────────

    def _error_result(
        self, call_type: str, *, jitter: bool, status: str
    ) -> dict:
        base = {
            "judge_status": status,
            "judge_quality": None,
            "judge_config_id": self._config_id,
            "judge_retry_jitter": jitter,
            "judge_input_tokens": None,
            "judge_output_tokens": None,
            "judge_cost_usd": None,
        }
        if call_type == "rubric":
            base.update(
                {
                    "completeness": None,
                    "accuracy": None,
                    "grounding": None,
                    "safety": None,
                    "rationale": None,
                    "confidence": None,
                    "judge_score": None,
                }
            )
        else:
            base.update({"errors": [], "annotation_confidence": None})
        return base
