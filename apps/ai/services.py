"""High-level service for running an AI generation.

Phase 2 ships the runtime building blocks. Phase 3 will wire these into
HTMX views and django-background-tasks; for now the function is callable
directly and is what tests exercise.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.ai.models import (
    AIGeneration,
    AIWorkspaceConfig,
    GenerationKind,
    GenerationStatus,
)
from apps.ai.pricing import cost_micro
from apps.ai.providers import ProviderError, ShroudBlockError, build_provider

logger = logging.getLogger(__name__)


class CapExceededError(Exception):
    """Raised when the workspace's monthly USD cap is exhausted."""


def _ensure_under_cap(workspace) -> AIWorkspaceConfig:
    config, _ = AIWorkspaceConfig.objects.get_or_create(workspace=workspace)
    config.roll_window_if_new_month()
    if config.is_over_cap():
        raise CapExceededError(
            f"Workspace '{workspace.name}' has hit its monthly AI cap "
            f"(${config.monthly_usd_cap}). Bump the cap in workspace settings."
        )
    return config


def run_generation(
    *,
    workspace,
    actor,
    kind: str,
    messages: list[dict[str, str]],
    input_payload: dict[str, Any],
    gtm_plan=None,
    model: str | None = None,
    provider: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    json_schema: dict | None = None,
) -> AIGeneration:
    """Run a single LLM generation and persist an AIGeneration row.

    Always returns the AIGeneration. On error the row is saved with status
    `failed` (or `blocked_by_shroud`) and `error_message` populated.
    """
    if kind not in dict(GenerationKind.choices):
        raise ValueError(f"Unknown kind: {kind}")

    config = _ensure_under_cap(workspace)
    chosen_model = model or config.default_model

    gen = AIGeneration.objects.create(
        workspace=workspace,
        actor=actor,
        kind=kind,
        gtm_plan=gtm_plan,
        input_payload=input_payload,
        provider=provider or "",
        model=chosen_model,
        routed_via_shroud=config.routed_via_shroud,
        status=GenerationStatus.RUNNING,
    )

    try:
        impl = build_provider(workspace, provider=provider)
        gen.provider = impl.name
        response = impl.generate(
            messages=messages,
            model=chosen_model,
            max_tokens=max_tokens,
            temperature=temperature,
            json_schema=json_schema,
        )
    except ShroudBlockError as exc:
        gen.status = GenerationStatus.BLOCKED_BY_SHROUD
        gen.error_message = str(exc)
        gen.completed_at = timezone.now()
        gen.save()
        return gen
    except (ProviderError, Exception) as exc:  # noqa: BLE001
        logger.exception("AI generation failed")
        gen.status = GenerationStatus.FAILED
        gen.error_message = str(exc)
        gen.completed_at = timezone.now()
        gen.save()
        return gen

    # Success: persist usage, redactions, cost
    prompt_tokens = response.usage.get("prompt_tokens", 0)
    completion_tokens = response.usage.get("completion_tokens", 0)
    micro = cost_micro(chosen_model, prompt_tokens, completion_tokens)

    gen.output_payload = {"text": response.text, "raw": response.raw}
    gen.shroud_redactions = response.redactions
    gen.prompt_tokens = prompt_tokens
    gen.completion_tokens = completion_tokens
    gen.cost_usd_micro = micro
    gen.latency_ms = response.latency_ms
    gen.status = GenerationStatus.SUCCEEDED
    gen.completed_at = timezone.now()
    gen.save()

    config.add_spend(micro)
    return gen
