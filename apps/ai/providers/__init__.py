"""Provider factory.

Resolves the workspace-configured provider, wraps it in Shroud routing if
the workspace's AIWorkspaceConfig has `routed_via_shroud=True`.

Provider keys come from apps.ai.models.AICredential (org-scoped, encrypted).
1Claw Vault integration is gated by AIWorkspaceConfig.use_oneclaw_vault — when
true, keys are fetched at request time from the Vault rather than from the DB.
"""

from __future__ import annotations

import os

from django.conf import settings

from apps.ai.models import AICredential, AICredentialKind, AIWorkspaceConfig
from apps.ai.providers.anthropic import AnthropicProvider
from apps.ai.providers.google import GoogleProvider
from apps.ai.providers.openai import OpenAIProvider
from apps.ai.providers.shroud import ShroudWrapper
from apps.ai.providers.types import (
    LLMProvider,
    LLMResponse,
    ProviderError,
    ShroudBlockError,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ProviderError",
    "ShroudBlockError",
    "build_provider",
    "PROVIDER_CLASSES",
]


PROVIDER_CLASSES = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "google": GoogleProvider,
}


_KIND_FOR_PROVIDER = {
    "anthropic": AICredentialKind.ANTHROPIC,
    "openai": AICredentialKind.OPENAI,
    "google": AICredentialKind.GOOGLE,
}


def _api_key_from_credential(org_id, provider: str) -> str | None:
    kind = _KIND_FOR_PROVIDER.get(provider)
    if not kind:
        return None
    cred = AICredential.objects.for_org(org_id).filter(kind=kind, is_configured=True).first()
    if cred and isinstance(cred.credentials, dict):
        return cred.credentials.get("api_key")
    return None


def _api_key_from_env(provider: str) -> str | None:
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_AI_API_KEY",
    }
    var = env_map.get(provider)
    if not var:
        return None
    return os.environ.get(var) or getattr(settings, var, None)


def _shroud_config(org_id) -> tuple[str | None, str | None]:
    """Return (endpoint, agent_token) from AICredential or settings."""
    endpoint = None
    token = None
    ep_cred = (
        AICredential.objects.for_org(org_id).filter(kind=AICredentialKind.SHROUD_ENDPOINT, is_configured=True).first()
    )
    tok_cred = (
        AICredential.objects.for_org(org_id)
        .filter(kind=AICredentialKind.SHROUD_AGENT_TOKEN, is_configured=True)
        .first()
    )
    if ep_cred and isinstance(ep_cred.credentials, dict):
        endpoint = ep_cred.credentials.get("endpoint")
    if tok_cred and isinstance(tok_cred.credentials, dict):
        token = tok_cred.credentials.get("token")

    endpoint = endpoint or os.environ.get("SHROUD_ENDPOINT") or getattr(settings, "SHROUD_ENDPOINT", None)
    return endpoint, token


def build_provider(workspace, *, provider: str | None = None) -> LLMProvider:
    """Construct a provider instance for this workspace.

    Resolution order:
      1. `provider` argument, if given
      2. AIWorkspaceConfig.provider_preference[0]
      3. settings.AI_DEFAULT_PROVIDER
    """
    config, _ = AIWorkspaceConfig.objects.get_or_create(workspace=workspace)
    chosen = (
        provider
        or (config.provider_preference[0] if config.provider_preference else None)
        or getattr(settings, "AI_DEFAULT_PROVIDER", "anthropic")
    )

    if chosen not in PROVIDER_CLASSES:
        raise ProviderError(f"Unknown provider: {chosen}")

    org_id = workspace.organization_id
    api_key = _api_key_from_credential(org_id, chosen) or _api_key_from_env(chosen)
    if not api_key:
        raise ProviderError(f"No API key configured for provider '{chosen}'. Add an AICredential or set the env var.")

    cls = PROVIDER_CLASSES[chosen]
    instance = cls(api_key=api_key)

    if config.routed_via_shroud:
        endpoint, token = _shroud_config(org_id)
        if not endpoint or not token:
            raise ProviderError("routed_via_shroud=True but Shroud endpoint/token not configured")
        # Shroud accepts the same body shape; swap base URL + bearer auth
        instance.base_url = endpoint.rstrip("/")
        instance.api_key = token  # underlying provider sees this as its api_key
        return ShroudWrapper(instance, agent_id=config.shroud_agent_id or "default")

    return instance
