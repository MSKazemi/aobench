"""Cost estimation — compute USD cost from token counts and model name."""

from __future__ import annotations

# Pricing table: model_name → (input_usd_per_1M, output_usd_per_1M)
# Prices as of early 2026; update as needed.
_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o":                (2.50,  10.00),
    "gpt-4o-mini":           (0.15,   0.60),
    "gpt-4-turbo":          (10.00,  30.00),
    "gpt-4":                (30.00,  60.00),
    "gpt-3.5-turbo":         (0.50,   1.50),
    "o1":                   (15.00,  60.00),
    "o1-mini":               (3.00,  12.00),
    "o3-mini":               (1.10,   4.40),
    # Claude
    "claude-opus-4-6":      (15.00,  75.00),
    "claude-sonnet-4-6":     (3.00,  15.00),
    "claude-haiku-4-5":      (0.80,   4.00),
}


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float | None:
    """Return estimated USD cost for a single API call, or None if model is unknown.

    Uses per-1M-token rates from *_PRICING*. Partial-name matching is attempted
    so that deployment names like ``"gpt-4o-2024-11"`` still resolve to ``"gpt-4o"``.
    """
    rate = _PRICING.get(model)
    if rate is None:
        # Partial-name fallback: longest key that appears as a substring of model
        matches = [(k, v) for k, v in _PRICING.items() if k in model]
        if matches:
            rate = max(matches, key=lambda kv: len(kv[0]))[1]
    if rate is None:
        return None
    input_rate, output_rate = rate
    return round(
        (prompt_tokens / 1_000_000) * input_rate
        + (completion_tokens / 1_000_000) * output_rate,
        6,
    )
