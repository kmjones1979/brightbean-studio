"""Shroud routing wrapper.

Wraps any underlying provider (Anthropic / OpenAI / Google) and rewrites the
HTTP layer to point at a Shroud TEE endpoint. Shroud is OpenAI/Anthropic-API
compatible — base URL swap + Authorization header swap + agent ID header.

Shroud-specific behaviors layered in:
- Capture redactions[] from response and surface on LLMResponse
- Detect injection_score blocks and raise ShroudBlockError
"""

from __future__ import annotations

from apps.ai.providers.types import LLMProvider, LLMResponse, ShroudBlockError


class ShroudWrapper:
    """Wraps a provider with Shroud routing.

    Construction:
        underlying = AnthropicProvider(api_key="sk-...")
        # Shroud accepts the same Anthropic-format body but at its own endpoint
        underlying.base_url = shroud_endpoint
        # Auth becomes a Bearer token (Shroud agent token)
        underlying.api_key = shroud_agent_token
        wrapped = ShroudWrapper(underlying, agent_id="agent_123")
    """

    name = "shroud"

    def __init__(self, underlying: LLMProvider, *, agent_id: str):
        self._underlying = underlying
        self._agent_id = agent_id
        # Inject the Shroud agent header on every call by mutating extra_headers
        if hasattr(underlying, "extra_headers"):
            underlying.extra_headers = {
                **(underlying.extra_headers or {}),
                "X-1Claw-Agent-Id": agent_id,
                "Authorization": f"Bearer {underlying.api_key}",
            }

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        response = self._underlying.generate(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            json_schema=json_schema,
        )

        # Shroud surfaces redactions[] and (optionally) blocked status in raw
        raw = response.raw or {}
        shroud_meta = raw.get("shroud") or raw.get("_shroud") or {}

        if shroud_meta.get("blocked"):
            reason = shroud_meta.get("reason", "Blocked by Shroud policy")
            raise ShroudBlockError(reason)

        redactions = shroud_meta.get("redactions") or []
        response.redactions = list(redactions)
        response.provider = "shroud"
        return response
