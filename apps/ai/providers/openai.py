"""OpenAI Chat Completions provider."""

from __future__ import annotations

from apps.ai.providers.base import HTTPProviderBase
from apps.ai.providers.types import LLMResponse


class OpenAIProvider(HTTPProviderBase):
    name = "openai"

    def __init__(self, *, api_key: str, base_url: str = "https://api.openai.com"):
        super().__init__(base_url=base_url, api_key=api_key)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
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
        body: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": json_schema, "strict": True},
            }

        data, elapsed, request_id = self._post_with_retry("/v1/chat/completions", body)

        text = ""
        choices = data.get("choices") or []
        if choices:
            text = (choices[0].get("message") or {}).get("content", "")

        usage_raw = data.get("usage") or {}
        usage = {
            "prompt_tokens": usage_raw.get("prompt_tokens", 0),
            "completion_tokens": usage_raw.get("completion_tokens", 0),
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
