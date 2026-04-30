"""Tests for the pricing module."""

from __future__ import annotations

import pytest

from apps.ai.pricing import cost_micro, known_models


@pytest.mark.parametrize(
    "model,prompt,completion,expected_micro",
    [
        # Sonnet 4.6: $3/M input, $15/M output
        ("claude-sonnet-4-6", 1000, 1000, 3_000 + 15_000),
        # Sonnet 4.6: 500 in / 100 out = (500*3 + 100*15) micro
        ("claude-sonnet-4-6", 500, 100, 1_500 + 1_500),
        # gpt-4o-mini: 150 input, 600 output per 1k
        ("gpt-4o-mini", 1000, 1000, 150 + 600),
        # gemini-2.5-flash: 75 in / 300 out per 1k
        ("gemini-2.5-flash", 2000, 1000, (75 * 2) + (300 * 1)),
        # Unknown model: opus rate fallback ($15/$75 per 1k)
        ("totally-unknown-model", 1000, 1000, 15_000 + 75_000),
    ],
)
def test_cost_micro(model, prompt, completion, expected_micro):
    assert cost_micro(model, prompt, completion) == expected_micro


def test_zero_tokens():
    assert cost_micro("claude-sonnet-4-6", 0, 0) == 0


def test_known_models_includes_modern_claude():
    models = known_models()
    assert "claude-sonnet-4-6" in models
    assert "gpt-4o" in models
    assert "gemini-2.5-flash" in models
