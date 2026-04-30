"""Tests for the provider factory + HTTP base.

We avoid real network calls by patching httpx.post.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from apps.ai.providers import ProviderError, build_provider
from apps.ai.providers.anthropic import AnthropicProvider
from apps.ai.providers.openai import OpenAIProvider
from apps.ai.providers.shroud import ShroudWrapper
from apps.ai.providers.stub import StubProvider
from apps.ai.providers.types import ShroudBlockError


def _mock_response(status: int = 200, body: dict | None = None, headers: dict | None = None):
    """Build a minimal httpx.Response for monkey-patched httpx.post."""
    request = httpx.Request("POST", "https://example.test")
    return httpx.Response(
        status_code=status,
        json=body if body is not None else {},
        headers=headers or {"x-request-id": "req_test"},
        request=request,
    )


class TestStubProvider:
    def test_returns_response(self):
        s = StubProvider(text="hello", prompt_tokens=10, completion_tokens=5)
        resp = s.generate(messages=[{"role": "user", "content": "hi"}], model="x")
        assert resp.text == "hello"
        assert resp.usage == {"prompt_tokens": 10, "completion_tokens": 5}

    def test_raises_block(self):
        s = StubProvider(raise_block=True)
        with pytest.raises(ShroudBlockError):
            s.generate(messages=[], model="x")


class TestAnthropicProvider:
    def test_generate_returns_text(self):
        body = {
            "content": [{"type": "text", "text": "Hello world"}],
            "model": "claude-sonnet-4-6",
            "usage": {"input_tokens": 7, "output_tokens": 3},
        }
        with patch("httpx.post", return_value=_mock_response(200, body)):
            provider = AnthropicProvider(api_key="sk-test")
            resp = provider.generate(
                messages=[{"role": "user", "content": "hi"}],
                model="claude-sonnet-4-6",
            )
        assert resp.text == "Hello world"
        assert resp.usage == {"prompt_tokens": 7, "completion_tokens": 3}
        assert resp.provider == "anthropic"
        assert resp.request_id == "req_test"

    def test_5xx_retries_once(self):
        first = _mock_response(503, {"error": "boom"})
        second = _mock_response(
            200, {"content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1}}
        )
        with patch("httpx.post", side_effect=[first, second]):
            provider = AnthropicProvider(api_key="sk-test")
            resp = provider.generate(messages=[{"role": "user", "content": "hi"}], model="x")
        assert resp.text == "ok"

    def test_4xx_no_retry(self):
        with patch("httpx.post", return_value=_mock_response(401, {"error": "unauth"})):
            provider = AnthropicProvider(api_key="bad")
            with pytest.raises(ProviderError, match="401"):
                provider.generate(messages=[{"role": "user", "content": "hi"}], model="x")

    def test_network_error_retries_once(self):
        timeout = httpx.TimeoutException("slow", request=httpx.Request("POST", "https://example.test"))
        ok = _mock_response(
            200, {"content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1}}
        )
        with patch("httpx.post", side_effect=[timeout, ok]):
            provider = AnthropicProvider(api_key="sk-test")
            resp = provider.generate(messages=[{"role": "user", "content": "hi"}], model="x")
        assert resp.text == "ok"

    def test_network_error_after_retry_raises(self):
        timeout = httpx.NetworkError("dead", request=httpx.Request("POST", "https://example.test"))
        with patch("httpx.post", side_effect=[timeout, timeout]):
            provider = AnthropicProvider(api_key="sk-test")
            with pytest.raises(ProviderError, match="network error"):
                provider.generate(messages=[{"role": "user", "content": "hi"}], model="x")

    def test_auth_header_present(self):
        captured = {}

        def fake_post(url, json, timeout, headers):
            captured["headers"] = headers
            return _mock_response(
                200, {"content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1}}
            )

        with patch("httpx.post", side_effect=fake_post):
            provider = AnthropicProvider(api_key="sk-the-key")
            provider.generate(messages=[{"role": "user", "content": "hi"}], model="x")
        assert captured["headers"]["x-api-key"] == "sk-the-key"
        assert captured["headers"]["anthropic-version"] == "2023-06-01"


class TestOpenAIProvider:
    def test_bearer_auth_header(self):
        captured = {}

        def fake_post(url, json, timeout, headers):
            captured["headers"] = headers
            return _mock_response(
                200,
                {"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}},
            )

        with patch("httpx.post", side_effect=fake_post):
            provider = OpenAIProvider(api_key="sk-openai")
            provider.generate(messages=[{"role": "user", "content": "hi"}], model="gpt-4o")
        assert captured["headers"]["Authorization"] == "Bearer sk-openai"

    def test_extracts_choice_text(self):
        body = {
            "choices": [{"message": {"content": "the answer"}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            "model": "gpt-4o",
        }
        with patch("httpx.post", return_value=_mock_response(200, body)):
            provider = OpenAIProvider(api_key="sk-test")
            resp = provider.generate(messages=[{"role": "user", "content": "hi"}], model="gpt-4o")
        assert resp.text == "the answer"
        assert resp.usage == {"prompt_tokens": 4, "completion_tokens": 2}


class TestShroudWrapper:
    def test_injects_agent_id_header(self):
        captured = {}

        def fake_post(url, json, timeout, headers):
            captured["headers"] = headers
            return _mock_response(
                200, {"content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1}}
            )

        with patch("httpx.post", side_effect=fake_post):
            inner = AnthropicProvider(api_key="agent-token-xyz")
            wrapped = ShroudWrapper(inner, agent_id="agent_42")
            wrapped.generate(messages=[{"role": "user", "content": "hi"}], model="x")
        assert captured["headers"]["X-1Claw-Agent-Id"] == "agent_42"
        assert captured["headers"]["Authorization"] == "Bearer agent-token-xyz"

    def test_blocked_response_raises(self):
        body = {
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "shroud": {"blocked": True, "reason": "Prompt injection score 0.95"},
        }
        with patch("httpx.post", return_value=_mock_response(200, body)):
            inner = AnthropicProvider(api_key="t")
            wrapped = ShroudWrapper(inner, agent_id="a")
            with pytest.raises(ShroudBlockError, match="Prompt injection"):
                wrapped.generate(messages=[{"role": "user", "content": "hi"}], model="x")

    def test_redactions_surfaced_on_response(self):
        body = {
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "shroud": {
                "redactions": [{"field": "secret_value", "matched": "STRIPE_KEY"}],
            },
        }
        with patch("httpx.post", return_value=_mock_response(200, body)):
            inner = AnthropicProvider(api_key="t")
            wrapped = ShroudWrapper(inner, agent_id="a")
            resp = wrapped.generate(messages=[{"role": "user", "content": "hi"}], model="x")
        assert resp.redactions == [{"field": "secret_value", "matched": "STRIPE_KEY"}]


@pytest.mark.django_db
class TestBuildProviderFactory:
    def test_unknown_provider_raises(self, workspace):
        with pytest.raises(ProviderError, match="Unknown provider"):
            build_provider(workspace, provider="not-a-real-provider")

    def test_no_credential_raises(self, workspace):
        # No env vars (assume tests run isolated), no credential row
        import os

        old = {k: os.environ.pop(k, None) for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_AI_API_KEY")}
        try:
            with pytest.raises(ProviderError, match="No API key"):
                build_provider(workspace, provider="anthropic")
        finally:
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v

    def test_with_credential_returns_provider(self, workspace, organization):
        from apps.ai.models import AICredential, AICredentialKind

        AICredential.objects.create(
            organization=organization,
            kind=AICredentialKind.ANTHROPIC,
            credentials={"api_key": "sk-test"},
            is_configured=True,
        )
        provider = build_provider(workspace, provider="anthropic")
        assert provider.name == "anthropic"
        assert provider.api_key == "sk-test"

    def test_shroud_routing_wraps_provider(self, workspace, organization):
        from apps.ai.models import (
            AICredential,
            AICredentialKind,
            AIWorkspaceConfig,
        )

        AICredential.objects.create(
            organization=organization,
            kind=AICredentialKind.ANTHROPIC,
            credentials={"api_key": "sk-test"},
            is_configured=True,
        )
        AICredential.objects.create(
            organization=organization,
            kind=AICredentialKind.SHROUD_ENDPOINT,
            credentials={"endpoint": "https://shroud.example.com"},
            is_configured=True,
        )
        AICredential.objects.create(
            organization=organization,
            kind=AICredentialKind.SHROUD_AGENT_TOKEN,
            credentials={"token": "shroud-token"},
            is_configured=True,
        )
        AIWorkspaceConfig.objects.update_or_create(
            workspace=workspace,
            defaults={
                "routed_via_shroud": True,
                "shroud_agent_id": "agent_test",
            },
        )
        provider = build_provider(workspace, provider="anthropic")
        assert isinstance(provider, ShroudWrapper)

    def test_shroud_routing_without_endpoint_raises(self, workspace, organization):
        from apps.ai.models import (
            AICredential,
            AICredentialKind,
            AIWorkspaceConfig,
        )

        AICredential.objects.create(
            organization=organization,
            kind=AICredentialKind.ANTHROPIC,
            credentials={"api_key": "sk-test"},
            is_configured=True,
        )
        AIWorkspaceConfig.objects.update_or_create(
            workspace=workspace,
            defaults={"routed_via_shroud": True},
        )
        with pytest.raises(ProviderError, match="Shroud endpoint"):
            build_provider(workspace, provider="anthropic")
