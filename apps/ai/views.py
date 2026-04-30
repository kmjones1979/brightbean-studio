"""AI app views — workspace settings page (Phase 2).

Generation endpoints land in Phase 3.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.ai.forms import AIWorkspaceConfigForm
from apps.ai.models import AIGeneration, AIWorkspaceConfig
from apps.ai.pricing import known_models
from apps.members.decorators import require_workspace_role


@require_workspace_role("manager")
@require_http_methods(["GET", "POST"])
def settings_page(request, workspace_id):
    workspace = request.workspace
    config, _ = AIWorkspaceConfig.objects.get_or_create(workspace=workspace)

    if request.method == "POST":
        form = AIWorkspaceConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "AI settings saved.")
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
