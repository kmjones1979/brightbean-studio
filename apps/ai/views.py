"""AI app views — workspace settings + generation endpoints (Phase 2 + 3)."""

from __future__ import annotations

import json
from decimal import Decimal

from django.contrib import messages as django_messages
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.ai.forms import AIWorkspaceConfigForm
from apps.ai.models import (
    AIGeneration,
    AIWorkspaceConfig,
    GenerationKind,
    GenerationStatus,
)
from apps.ai.platform_specs import PLATFORM_SPECS, supported_platforms
from apps.ai.pricing import known_models
from apps.ai.services import CapExceededError
from apps.gtm.models import GTMPlan
from apps.members.decorators import require_workspace_role

# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------


@require_workspace_role("manager")
@require_http_methods(["GET", "POST"])
def settings_page(request, workspace_id):
    workspace = request.workspace
    config, _ = AIWorkspaceConfig.objects.get_or_create(workspace=workspace)

    if request.method == "POST":
        form = AIWorkspaceConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            django_messages.success(request, "AI settings saved.")
            return redirect("ai:settings", workspace_id=workspace.id)
    else:
        form = AIWorkspaceConfigForm(instance=config)

    config.roll_window_if_new_month()
    spend_usd = Decimal(config.current_month_spend_micro) / Decimal(1_000_000)
    cap_usd = Decimal(config.monthly_usd_cap)

    recent_generations = AIGeneration.objects.for_workspace(workspace.id).order_by("-created_at")[:10]

    return render(
        request,
        "ai/settings.html",
        {
            "workspace": workspace,
            "form": form,
            "config": config,
            "spend_usd": spend_usd,
            "cap_usd": cap_usd,
            "spend_pct": (int((spend_usd / cap_usd) * 100) if cap_usd > 0 else 0),
            "available_models": known_models(),
            "recent_generations": recent_generations,
        },
    )


# ---------------------------------------------------------------------------
# Generation kinds (Phase 3): caption + multi_platform
# ---------------------------------------------------------------------------


def _queue_generation(
    *,
    workspace,
    actor,
    kind: str,
    input_payload: dict,
    gtm_plan_id: str | None,
) -> AIGeneration:
    """Persist a queued AIGeneration row and schedule the worker task."""
    from apps.ai.tasks import run_generation_task

    config, _ = AIWorkspaceConfig.objects.get_or_create(workspace=workspace)
    if config.is_over_cap():
        raise CapExceededError(f"Workspace '{workspace.name}' has hit its monthly AI cap (${config.monthly_usd_cap}).")

    gtm_plan = None
    if gtm_plan_id:
        gtm_plan = GTMPlan.objects.for_workspace(workspace.id).filter(id=gtm_plan_id).first()

    gen = AIGeneration.objects.create(
        workspace=workspace,
        actor=actor,
        kind=kind,
        gtm_plan=gtm_plan,
        input_payload=input_payload,
        provider="",
        model=config.default_model,
        routed_via_shroud=config.routed_via_shroud,
        status=GenerationStatus.QUEUED,
    )

    # Schedule the worker. Background tasks run when the worker process picks
    # them up; in tests we patch this out.
    run_generation_task(str(gen.id))
    return gen


@require_workspace_role("editor")
@require_POST
def generate_caption(request, workspace_id):
    workspace = request.workspace
    brief = (request.POST.get("brief") or "").strip()
    platform = request.POST.get("platform") or "twitter"
    gtm_plan_id = request.POST.get("gtm_plan_id") or None

    if not brief:
        return HttpResponseBadRequest("brief is required")
    if platform not in supported_platforms():
        return HttpResponseBadRequest(f"unknown platform '{platform}'")

    try:
        gen = _queue_generation(
            workspace=workspace,
            actor=request.user,
            kind=GenerationKind.CAPTION,
            input_payload={"brief": brief, "platform": platform},
            gtm_plan_id=gtm_plan_id,
        )
    except CapExceededError as exc:
        return render(
            request,
            "ai/partials/cap_exceeded.html",
            {"workspace": workspace, "error": str(exc)},
            status=429,
        )

    return render(
        request,
        "ai/partials/generation_pending.html",
        {"workspace": workspace, "generation": gen},
    )


@require_workspace_role("editor")
@require_POST
def generate_multi_platform(request, workspace_id):
    workspace = request.workspace
    brief = (request.POST.get("brief") or "").strip()
    platforms = request.POST.getlist("platforms[]") or request.POST.getlist("platforms")
    gtm_plan_id = request.POST.get("gtm_plan_id") or None

    if not brief:
        return HttpResponseBadRequest("brief is required")
    if not platforms:
        return HttpResponseBadRequest("at least one platform is required")

    invalid = [p for p in platforms if p not in supported_platforms()]
    if invalid:
        return HttpResponseBadRequest(f"unknown platforms: {invalid}")

    try:
        gen = _queue_generation(
            workspace=workspace,
            actor=request.user,
            kind=GenerationKind.MULTI_PLATFORM,
            input_payload={"brief": brief, "platforms": list(platforms)},
            gtm_plan_id=gtm_plan_id,
        )
    except CapExceededError as exc:
        return render(
            request,
            "ai/partials/cap_exceeded.html",
            {"workspace": workspace, "error": str(exc)},
            status=429,
        )

    return render(
        request,
        "ai/partials/generation_pending.html",
        {"workspace": workspace, "generation": gen},
    )


@require_workspace_role("viewer")
@require_GET
def generation_poll(request, workspace_id, generation_id):
    """HTMX poller. Returns either the pending partial (poll again) or the
    final result partial (stop polling)."""
    workspace = request.workspace
    gen = get_object_or_404(AIGeneration.objects.for_workspace(workspace.id), id=generation_id)

    parsed_output = None
    if gen.status == GenerationStatus.SUCCEEDED:
        text = (gen.output_payload or {}).get("text", "")
        try:
            parsed_output = json.loads(text)
        except (TypeError, ValueError):
            parsed_output = {"text": text}

    return render(
        request,
        "ai/partials/generation_result.html",
        {
            "workspace": workspace,
            "generation": gen,
            "parsed": parsed_output,
            "is_terminal": gen.status
            in (
                GenerationStatus.SUCCEEDED,
                GenerationStatus.FAILED,
                GenerationStatus.BLOCKED_BY_SHROUD,
            ),
        },
    )


@require_workspace_role("viewer")
@require_GET
def generate_panel(request, workspace_id):
    """Standalone view of the generate panel — used as the composer's AI tab.

    Always renders the panel expanded with the active GTM plan pre-selected
    so the AI flow is the primary affordance, not a hidden secondary action.
    """
    workspace = request.workspace
    plans = GTMPlan.objects.for_workspace(workspace.id).filter(status="active").select_related("partner", "product")
    if not plans.exists():
        plans = GTMPlan.objects.for_workspace(workspace.id).select_related("partner", "product")
    selected_plan_id = request.GET.get("gtm_plan_id") or (str(plans.first().id) if plans.exists() else "")
    return render(
        request,
        "ai/generate_panel.html",
        {
            "workspace": workspace,
            "plans": plans,
            "selected_plan_id": selected_plan_id,
            "platform_specs": PLATFORM_SPECS,
            "default_platform": "twitter",
        },
    )
