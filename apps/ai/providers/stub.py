"""In-memory stub provider for tests and `--demo-content` seeding.

Never makes a network call. Returns deterministic fixture text.
"""

from __future__ import annotations

from apps.ai.providers.types import LLMResponse


class StubProvider:
    name = "stub"

    def __init__(
        self,
        *,
        text: str = "stubbed response",
        prompt_tokens: int = 100,
        completion_tokens: int = 50,
        latency_ms: int = 12,
        redactions: list | None = None,
        raise_block: bool = False,
        raise_error: Exception | None = None,
    ):
        self._text = text
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self._latency_ms = latency_ms
        self._redactions = redactions or []
        self._raise_block = raise_block
        self._raise_error = raise_error

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        from apps.ai.providers.types import ShroudBlockError

        if self._raise_error:
            raise self._raise_error
        if self._raise_block:
            raise ShroudBlockError("Blocked by stub")

        return LLMResponse(
            text=self._text,
            usage={
                "prompt_tokens": self._prompt_tokens,
                "completion_tokens": self._completion_tokens,
            },
            provider=self.name,
            model=model,
            latency_ms=self._latency_ms,
            redactions=list(self._redactions),
        )
