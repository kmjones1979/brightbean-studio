"""Background tasks for AI generation.

Each generation is queued as a row in AIGeneration with status='queued',
then a background_task picks it up and runs it via services.run_generation.
HTMX clients poll the generation row to render progress / final result.
"""

from __future__ import annotations

import logging
from typing import Any

from background_task import background

from apps.ai.models import AIGeneration, GenerationStatus
from apps.ai.prompts import render_prompt

logger = logging.getLogger(__name__)


@background(schedule=0)
def run_generation_task(generation_id: str) -> None:
    """Worker entrypoint: hydrate the AIGeneration row, render its prompt,
    invoke the provider, persist the outcome.
    """
    from apps.ai.services import _ensure_under_cap

    try:
        gen = AIGeneration.objects.select_related("workspace", "gtm_plan").get(id=generation_id)
    except AIGeneration.DoesNotExist:
        logger.warning("AIGeneration %s vanished before worker picked it up", generation_id)
        return

    if gen.status not in (GenerationStatus.QUEUED, GenerationStatus.RUNNING):
        logger.info("AIGeneration %s already in status %s — skipping", generation_id, gen.status)
        return

    payload: dict[str, Any] = gen.input_payload or {}
    brief = payload.get("brief", "")
    platform = payload.get("platform")
    platforms = payload.get("platforms")

    try:
        rendered, schema = render_prompt(
            gen.kind,
            gtm_plan=gen.gtm_plan,
            brief=brief,
            platform=platform,
            platforms=platforms,
            extra=payload.get("extra"),
        )
    except FileNotFoundError as exc:
        gen.status = GenerationStatus.FAILED
        gen.error_message = f"No prompt template for kind '{gen.kind}': {exc}"
        gen.save()
        return

    messages = [
        {"role": "system", "content": rendered},
        {"role": "user", "content": brief},
    ]

    # Cap is checked again here in case the worker runs much later than queueing
    try:
        _ensure_under_cap(gen.workspace)
    except Exception as exc:  # noqa: BLE001
        gen.status = GenerationStatus.FAILED
        gen.error_message = str(exc)
        gen.save()
        return

    # Delegate the actual call. We inline by recreating the gen via run_generation
    # would be wasteful — instead we patch the existing gen by reusing the
    # provider invocation path.
    from django.utils import timezone

    from apps.ai.models import AIWorkspaceConfig
    from apps.ai.pricing import cost_micro
    from apps.ai.providers import ProviderError, ShroudBlockError, build_provider

    config, _ = AIWorkspaceConfig.objects.get_or_create(workspace=gen.workspace)
    chosen_model = gen.model or config.default_model

    gen.status = GenerationStatus.RUNNING
    gen.save(update_fields=["status"])

    try:
        impl = build_provider(gen.workspace, provider=gen.provider or None)
        gen.provider = impl.name
        response = impl.generate(
            messages=messages,
            model=chosen_model,
            max_tokens=payload.get("max_tokens", 1024),
            temperature=payload.get("temperature", 0.7),
            json_schema=schema,
        )
    except ShroudBlockError as exc:
        gen.status = GenerationStatus.BLOCKED_BY_SHROUD
        gen.error_message = str(exc)
        gen.completed_at = timezone.now()
        gen.save()
        return
    except (ProviderError, Exception) as exc:  # noqa: BLE001
        logger.exception("Background AI generation failed")
        gen.status = GenerationStatus.FAILED
        gen.error_message = str(exc)
        gen.completed_at = timezone.now()
        gen.save()
        return

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
