"""Pricing table for LLM models. Rates in USD micro-dollars per 1K tokens.

1 USD = 1,000,000 micro-dollars. Storing as int avoids float drift.

Rates are approximate published list prices as of 2026-Q2 — update as
providers change pricing. Unknown models fall back to the most-expensive
rate to err on the side of over-counting cost (so the cap triggers earlier).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRate:
    """Cost per 1,000 tokens, in USD micro-dollars."""

    input_micro_per_1k: int
    output_micro_per_1k: int


# Anthropic Claude
_ANTHROPIC = {
    "claude-opus-4-7": ModelRate(15_000, 75_000),
    "claude-opus-4-6": ModelRate(15_000, 75_000),
    "claude-opus-4-5": ModelRate(15_000, 75_000),
    "claude-sonnet-4-7": ModelRate(3_000, 15_000),
    "claude-sonnet-4-6": ModelRate(3_000, 15_000),
    "claude-sonnet-4-5": ModelRate(3_000, 15_000),
    "claude-haiku-4-5": ModelRate(1_000, 5_000),
    "claude-3-5-sonnet-20241022": ModelRate(3_000, 15_000),
    "claude-3-haiku-20240307": ModelRate(250, 1_250),
}

# OpenAI
_OPENAI = {
    "gpt-4o": ModelRate(2_500, 10_000),
    "gpt-4o-mini": ModelRate(150, 600),
    "gpt-4-turbo": ModelRate(10_000, 30_000),
    "gpt-4": ModelRate(30_000, 60_000),
    "gpt-3.5-turbo": ModelRate(500, 1_500),
}

# Google Gemini
_GOOGLE = {
    "gemini-2.5-pro": ModelRate(1_250, 5_000),
    "gemini-2.5-flash": ModelRate(75, 300),
    "gemini-1.5-pro": ModelRate(1_250, 5_000),
    "gemini-1.5-flash": ModelRate(75, 300),
}


_ALL_RATES: dict[str, ModelRate] = {**_ANTHROPIC, **_OPENAI, **_GOOGLE}


# Conservative fallback — Opus-class pricing
_DEFAULT_RATE = ModelRate(15_000, 75_000)


def cost_micro(model: str, prompt_tokens: int, completion_tokens: int) -> int:
    """Compute the cost of a single LLM call in USD micro-dollars."""
    rate = _ALL_RATES.get(model, _DEFAULT_RATE)
    input_cost = (prompt_tokens * rate.input_micro_per_1k) // 1000
    output_cost = (completion_tokens * rate.output_micro_per_1k) // 1000
    return input_cost + output_cost


def known_models() -> list[str]:
    return sorted(_ALL_RATES.keys())
