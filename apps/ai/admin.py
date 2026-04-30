from django.contrib import admin

from apps.ai.models import AICredential, AIGeneration, AIPreset, AIWorkspaceConfig


@admin.register(AICredential)
class AICredentialAdmin(admin.ModelAdmin):
    list_display = ("organization", "kind", "is_configured", "updated_at")
    list_filter = ("kind", "is_configured")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AIGeneration)
class AIGenerationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "kind",
        "workspace",
        "provider",
        "model",
        "status",
        "cost_usd",
        "created_at",
    )
    list_filter = ("kind", "status", "provider", "routed_via_shroud", "workspace")
    search_fields = ("id", "model", "error_message")
    readonly_fields = (
        "id",
        "input_payload",
        "output_payload",
        "shroud_redactions",
        "prompt_tokens",
        "completion_tokens",
        "cost_usd_micro",
        "latency_ms",
        "created_at",
        "completed_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(AIPreset)
class AIPresetAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "actor", "provider", "model")
    list_filter = ("workspace", "provider")
    search_fields = ("name",)


@admin.register(AIWorkspaceConfig)
class AIWorkspaceConfigAdmin(admin.ModelAdmin):
    list_display = (
        "workspace",
        "default_model",
        "monthly_usd_cap",
        "routed_via_shroud",
        "use_oneclaw_vault",
    )
    list_filter = ("routed_via_shroud", "use_oneclaw_vault")
    readonly_fields = ("current_month_spend_micro", "spend_window_start")
