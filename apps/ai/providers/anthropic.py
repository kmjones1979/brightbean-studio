"""Anthropic Claude provider."""

from __future__ import annotations

from apps.ai.providers.base import HTTPProviderBase
from apps.ai.providers.types import LLMResponse


class AnthropicProvider(HTTPProviderBase):
    name = "anthropic"

    def __init__(self, *, api_key: str, base_url: str = "https://api.anthropic.com"):
        super().__init__(base_url=base_url, api_key=api_key)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            **self.extra_headers,
        }

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        # Anthropic separates system vs user/assistant
        system_text = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        non_system = [m for m in messages if m.get("role") != "system"]

        body: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": non_system,
        }
        if system_text:
            body["system"] = system_text

        # Anthropic supports tool-based structured output; for v1 we ask for JSON
        # in the system prompt (simpler) and validate downstream.

        data, elapsed, request_id = self._post_with_retry("/v1/messages", body)

        text = ""
        if data.get("content"):
            for block in data["content"]:
                if block.get("type") == "text":
                    text += block.get("text", "")

        usage_raw = data.get("usage") or {}
        usage = {
            "prompt_tokens": usage_raw.get("input_tokens", 0),
            "completion_tokens": usage_raw.get("output_tokens", 0),
        }

        return LLMResponse(
            text=text,
            usage=usage,
            provider=self.name,
            model=data.get("model", model),
            latency_ms=elapsed,
            request_id=request_id,
            raw=data,
        )
