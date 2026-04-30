"""Shared provider types: LLMResponse, LLMProvider protocol, ProviderError."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(Exception):
    """Raised when a provider call fails after retries."""


class ShroudBlockError(ProviderError):
    """Raised when Shroud refuses to forward (injection threshold exceeded etc.)."""


@dataclass
class LLMResponse:
    """Provider-agnostic response shape."""

    text: str
    usage: dict[str, int] = field(default_factory=dict)  # prompt_tokens, completion_tokens
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    request_id: str = ""
    redactions: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    """Every concrete provider implements this interface."""

    name: str

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        json_schema: dict | None = None,
    ) -> LLMResponse: ...
