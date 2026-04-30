from django.contrib import admin

from apps.gtm.models import (
    GTMPlan,
    GTMPlanRevision,
    Partner,
    ProblemSolution,
    Product,
)


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "is_archived", "created_at")
    list_filter = ("is_archived", "workspace")
    search_fields = ("name", "website")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "partner", "category", "is_archived")
    list_filter = ("is_archived", "partner")
    search_fields = ("name", "tagline")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("partner",)


@admin.register(ProblemSolution)
class ProblemSolutionAdmin(admin.ModelAdmin):
    list_display = ("target_persona", "product", "pain_intensity", "is_primary")
    list_filter = ("is_primary", "pain_intensity", "product")
    search_fields = ("target_persona", "problem_statement")
    autocomplete_fields = ("product",)


@admin.register(GTMPlan)
class GTMPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "partner",
        "product",
        "status",
        "workspace",
        "updated_at",
    )
    list_filter = ("status", "workspace", "partner")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("partner", "product", "problem_solution")
    readonly_fields = ("created_at", "updated_at")


@admin.register(GTMPlanRevision)
class GTMPlanRevisionAdmin(admin.ModelAdmin):
    list_display = ("plan", "diff_summary", "edited_by", "created_at")
    list_filter = ("plan",)
    readonly_fields = ("plan", "snapshot", "diff_summary", "edited_by", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
