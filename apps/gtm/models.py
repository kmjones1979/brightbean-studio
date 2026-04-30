"""GTM (Go-To-Market) plan models.

A GTMPlan is structured context (audiences, value props, claims, voice) used
as the source of truth for AI content generation. Plans are scoped per
Partner / Product / ProblemSolution.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.managers import WorkspaceScopedModel


class Partner(WorkspaceScopedModel):
    """The entity a GTM plan targets (e.g., '1Claw', 'Acme Corp')."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="gtm/partners/%Y/%m/", blank=True)
    notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gtm_partner"
        ordering = ["name"]
        unique_together = [("workspace", "slug")]
        indexes = [
            models.Index(fields=["workspace", "is_archived"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)


class Product(models.Model):
    """A product offered by a Partner. Examples for 1Claw: Shroud, Intents, Vault."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    tagline = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=100, blank=True)
    homepage_url = models.URLField(blank=True)
    docs_url = models.URLField(blank=True)
    pricing_url = models.URLField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gtm_product"
        ordering = ["name"]
        unique_together = [("partner", "slug")]

    def __str__(self) -> str:
        return f"{self.partner.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)


class ProblemSolution(models.Model):
    """A problem/solution pair targeted at a specific persona, scoped to a Product."""

    PAIN_INTENSITY_CHOICES = [
        (1, "1 - Mild"),
        (2, "2 - Moderate"),
        (3, "3 - Significant"),
        (4, "4 - Severe"),
        (5, "5 - Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="problem_solutions",
    )
    problem_statement = models.TextField(
        help_text="Markdown. The pain in the customer's words.",
    )
    solution_statement = models.TextField(
        help_text="Markdown. How the product solves it.",
    )
    target_persona = models.CharField(max_length=200)
    pain_intensity = models.PositiveSmallIntegerField(
        choices=PAIN_INTENSITY_CHOICES,
        default=3,
    )
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gtm_problem_solution"
        ordering = ["-is_primary", "-pain_intensity", "target_persona"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="gtm_problem_solution_one_primary_per_product",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.name}: {self.target_persona}"


class GTMPlanStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class GTMPlan(WorkspaceScopedModel):
    """The unit of context fed to AI generation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name="gtm_plans",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="gtm_plans",
        null=True,
        blank=True,
        help_text="Null = partner-wide plan",
    )
    problem_solution = models.ForeignKey(
        ProblemSolution,
        on_delete=models.PROTECT,
        related_name="gtm_plans",
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    status = models.CharField(
        max_length=20,
        choices=GTMPlanStatus.choices,
        default=GTMPlanStatus.DRAFT,
    )

    # Structured plan content (JSON)
    audiences = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {persona, role_titles, company_size, industries, watering_holes}",
    )
    value_props = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of value-proposition strings (max 8)",
    )
    proof_points = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {claim, evidence_url, evidence_type}",
    )
    voice = models.JSONField(
        default=dict,
        blank=True,
        help_text="{tone, formality_1_to_5, humor_allowed, emoji_policy, we_vs_i, reading_level}",
    )
    do_say = models.JSONField(
        default=list,
        blank=True,
        help_text="Preferred phrases / framings",
    )
    do_not_say = models.JSONField(
        default=list,
        blank=True,
        help_text="Banned words, competitor names to avoid, regulated claims",
    )
    competitors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {name, positioning_against}",
    )
    keywords_seo = models.JSONField(
        default=list,
        blank=True,
    )
    cta_library = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {label, url, intent}",
    )
    compliance_notes = models.TextField(blank=True)

    # Optional FK to media library folder
    linked_media_folder = models.ForeignKey(
        "media_library.MediaFolder",
        on_delete=models.SET_NULL,
        related_name="gtm_plans",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="gtm_plans_created",
        null=True,
    )
    last_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="gtm_plans_edited",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gtm_plan"
        ordering = ["-updated_at"]
        unique_together = [("workspace", "slug")]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["partner", "product"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)

    @property
    def is_archived(self) -> bool:
        return self.status == GTMPlanStatus.ARCHIVED


class GTMPlanRevision(models.Model):
    """Append-only snapshot of a GTMPlan, captured on save.

    Powers the History tab; never edited or deleted via UI.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        GTMPlan,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    snapshot = models.JSONField(
        help_text="Full GTMPlan state at the time of revision (JSON-serialized)",
    )
    diff_summary = models.CharField(
        max_length=500,
        blank=True,
        help_text="Human-readable summary of changes from the previous revision",
    )
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="gtm_plan_revisions",
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gtm_plan_revision"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["plan", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.plan.name} revision {self.created_at:%Y-%m-%d %H:%M}"
