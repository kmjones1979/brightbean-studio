"""AI generation models.

The provider layer writes one AIGeneration row per LLM call — capturing the
input, output, provider, model, redactions, latency, and cost. AIWorkspaceConfig
holds per-workspace defaults (provider, model, monthly cap, Shroud routing).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.encryption import EncryptedJSONField
from apps.common.managers import OrgScopedManager, WorkspaceScopedModel


class AICredentialKind(models.TextChoices):
    ANTHROPIC = "ai_anthropic", "Anthropic API key"
    OPENAI = "ai_openai", "OpenAI API key"
    GOOGLE = "ai_google", "Google AI API key"
    SHROUD_ENDPOINT = "ai_shroud_endpoint", "1Claw Shroud endpoint"
    SHROUD_AGENT_TOKEN = "ai_shroud_agent_token", "1Claw Shroud agent token"
    ONECLAW_VAULT_TOKEN = "ai_1claw_vault_token", "1Claw Vault agent token"


class AICredential(models.Model):
    """Per-org encrypted store for AI provider keys + Shroud / Vault config.

    Reuses the EncryptedJSONField pattern from apps.common (same encryption
    infrastructure as apps/credentials/PlatformCredential), but lives in
    apps/ai so the publishing-platform connect UI is not polluted with
    LLM-provider entries.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_credentials",
    )
    kind = models.CharField(max_length=40, choices=AICredentialKind.choices)
    credentials = EncryptedJSONField(
        default=dict,
        help_text="Encrypted JSON, e.g. {'api_key': '...'} or {'endpoint': '...'}",
    )
    is_configured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgScopedManager()

    class Meta:
        db_table = "ai_credential"
        unique_together = [("organization", "kind")]

    def __str__(self) -> str:
        return f"{self.organization.name} — {self.get_kind_display()}"


class GenerationKind(models.TextChoices):
    CAPTION = "caption", "Caption"
    MULTI_PLATFORM = "multi_platform", "Multi-Platform"
    HOOK = "hook", "Hook"
    CTA = "cta", "CTA"
    HASHTAGS = "hashtags", "Hashtags"
    BRIEF_EXPAND = "brief_expand", "Brief Expand"
    IDEA_SEED = "idea_seed", "Idea Seed"
    REPLY_DRAFT = "reply_draft", "Reply Draft"
    IMAGE_PROMPT = "image_prompt", "Image Prompt"


class GenerationStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    BLOCKED_BY_SHROUD = "blocked_by_shroud", "Blocked by Shroud"


class AIGeneration(WorkspaceScopedModel):
    """One row per LLM call. Auditable, costed, and Shroud-trackable."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_generations",
        null=True,
    )
    kind = models.CharField(max_length=30, choices=GenerationKind.choices)

    gtm_plan = models.ForeignKey(
        "gtm.GTMPlan",
        on_delete=models.SET_NULL,
        related_name="generations",
        null=True,
        blank=True,
    )

    # Input
    input_payload = models.JSONField(default=dict, help_text="Brief, options, etc.")
    system_prompt_version = models.CharField(max_length=50, default="v0")

    # Provider routing
    provider = models.CharField(
        max_length=50,
        help_text="anthropic / openai / google",
    )
    model = models.CharField(max_length=100)
    routed_via_shroud = models.BooleanField(default=False)
    shroud_redactions = models.JSONField(
        default=list,
        blank=True,
        help_text="Verbatim copy of Shroud's redactions array, if present",
    )

    # Output
    output_payload = models.JSONField(default=dict, blank=True)

    # Cost & metering
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    cost_usd_micro = models.PositiveBigIntegerField(
        default=0,
        help_text="USD micro-dollars (1 USD = 1,000,000 micro). Avoids float drift.",
    )
    latency_ms = models.PositiveIntegerField(default=0)

    # Lifecycle
    status = models.CharField(
        max_length=30,
        choices=GenerationStatus.choices,
        default=GenerationStatus.QUEUED,
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_generation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "kind", "-created_at"]),
            models.Index(fields=["workspace", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.id} ({self.status})"

    @property
    def cost_usd(self) -> Decimal:
        return Decimal(self.cost_usd_micro) / Decimal(1_000_000)


class AIPreset(WorkspaceScopedModel):
    """Saved generation settings (model, temp, default GTM plan) per user/workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_presets",
    )
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=100, blank=True)
    temperature = models.FloatField(default=0.7)
    default_gtm_plan = models.ForeignKey(
        "gtm.GTMPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_preset"
        ordering = ["name"]
        unique_together = [("workspace", "actor", "name")]


class AIWorkspaceConfig(models.Model):
    """Singleton-per-workspace AI config: provider preference, default model,
    monthly cap, current month spend, Shroud routing, 1Claw Vault toggle.
    """

    DEFAULT_MONTHLY_CAP_USD = 25

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="ai_config",
    )
    provider_preference = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of providers, e.g. ['anthropic', 'openai']",
    )
    default_model = models.CharField(max_length=100, default="claude-sonnet-4-6")

    monthly_usd_cap = models.PositiveIntegerField(
        default=DEFAULT_MONTHLY_CAP_USD,
        help_text="Whole USD per month per workspace",
    )
    current_month_spend_micro = models.PositiveBigIntegerField(default=0)
    spend_window_start = models.DateField(default=timezone.now)

    # Shroud routing
    routed_via_shroud = models.BooleanField(default=False)
    shroud_agent_id = models.CharField(max_length=200, blank=True)

    # 1Claw Vault: fetch LLM keys from Vault rather than locally stored creds
    use_oneclaw_vault = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_workspace_config"

    def __str__(self) -> str:
        return f"AI config for {self.workspace.name}"

    @property
    def monthly_cap_micro(self) -> int:
        return int(self.monthly_usd_cap) * 1_000_000

    @property
    def cap_remaining_micro(self) -> int:
        return max(0, self.monthly_cap_micro - self.current_month_spend_micro)

    def is_over_cap(self) -> bool:
        return self.current_month_spend_micro >= self.monthly_cap_micro

    def roll_window_if_new_month(self, now: datetime | None = None) -> bool:
        """If we've crossed a calendar month boundary, reset month spend.
        Returns True if rolled.
        """
        now = now or timezone.now()
        today = now.date() if hasattr(now, "date") else now
        if today.year != self.spend_window_start.year or today.month != self.spend_window_start.month:
            self.current_month_spend_micro = 0
            self.spend_window_start = today.replace(day=1)
            return True
        return False

    def add_spend(self, micro: int) -> None:
        self.roll_window_if_new_month()
        self.current_month_spend_micro += micro
        self.save(update_fields=["current_month_spend_micro", "spend_window_start", "updated_at"])
