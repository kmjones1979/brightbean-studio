"""Google Gemini provider — uses generateContent endpoint."""

from __future__ import annotations

from apps.ai.providers.base import HTTPProviderBase
from apps.ai.providers.types import LLMResponse


class GoogleProvider(HTTPProviderBase):
    name = "google"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com",
    ):
        super().__init__(base_url=base_url, api_key=api_key)

    def _auth_headers(self) -> dict[str, str]:
        # Google takes the key as a query param OR a header. We use the header
        # form (x-goog-api-key) which works for the Generative Language API.
        return {
            "x-goog-api-key": self.api_key,
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
        # Convert (role, content) messages to Gemini's contents/parts shape
        contents = []
        system_instruction = None
        for msg in messages:
            role = msg.get("role")
            text = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": text}]}
            else:
                # Gemini uses 'user' / 'model'
                gemini_role = "user" if role == "user" else "model"
                contents.append({"role": gemini_role, "parts": [{"text": text}]})

        body: dict = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_instruction:
            body["systemInstruction"] = system_instruction
        if json_schema:
            body["generationConfig"]["responseMimeType"] = "application/json"
            body["generationConfig"]["responseSchema"] = json_schema

        data, elapsed, request_id = self._post_with_retry(f"/v1beta/models/{model}:generateContent", body)

        text = ""
        candidates = data.get("candidates") or []
        if candidates:
            for part in (candidates[0].get("content") or {}).get("parts", []):
                text += part.get("text", "")

        usage_raw = data.get("usageMetadata") or {}
        usage = {
            "prompt_tokens": usage_raw.get("promptTokenCount", 0),
            "completion_tokens": usage_raw.get("candidatesTokenCount", 0),
        }

        return LLMResponse(
            text=text,
            usage=usage,
            provider=self.name,
            model=model,
            latency_ms=elapsed,
            request_id=request_id,
            raw=data,
        )
