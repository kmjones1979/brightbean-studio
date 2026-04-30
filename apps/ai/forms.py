"""Forms for AI workspace settings."""

from __future__ import annotations

from django import forms

from apps.ai.models import AIWorkspaceConfig

_INPUT = "w-full px-3 py-2 rounded-lg border border-stone-200 focus:border-stone-400 focus:outline-none text-sm"


class AIWorkspaceConfigForm(forms.ModelForm):
    class Meta:
        model = AIWorkspaceConfig
        fields = (
            "default_model",
            "monthly_usd_cap",
            "routed_via_shroud",
            "shroud_agent_id",
            "use_oneclaw_vault",
        )
        widgets = {
            "default_model": forms.TextInput(attrs={"class": _INPUT}),
            "monthly_usd_cap": forms.NumberInput(attrs={"class": _INPUT}),
            "shroud_agent_id": forms.TextInput(attrs={"class": _INPUT}),
        }
