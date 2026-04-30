"""Views for the GTM app.

All views are workspace-scoped via the URL kwarg `workspace_id` which the
RBACMiddleware uses to populate `request.workspace` and
`request.workspace_membership`.

HTMX conventions:
- POST/PUT/DELETE actions return the updated partial (outerHTML swap)
- Modals open via hx-get returning the modal partial
- The `_role` decorator factory below maps the GTM-specific role mapping
  (viewer=read, editor=create/edit, owner=archive/delete) onto the
  workspace's broader role hierarchy.
"""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.gtm import forms as gtm_forms
from apps.gtm.models import (
    GTMPlan,
    GTMPlanRevision,
    GTMPlanStatus,
    Partner,
    ProblemSolution,
    Product,
)
from apps.members.decorators import require_workspace_role

# GTM permission mapping:
#   viewer  -> can read everything
#   editor  -> create/edit (matches workspace 'editor' or above)
#   owner   -> archive/delete (matches workspace 'owner' or 'manager')
ROLE_VIEW = "viewer"
ROLE_EDIT = "editor"
ROLE_ADMIN = "manager"


# --------------------------------------------------------------------------
# Plan list & detail
# --------------------------------------------------------------------------


@require_workspace_role(ROLE_VIEW)
def plan_list(request: HttpRequest, workspace_id):
    workspace = request.workspace
    status_filter = request.GET.get("status", "")
    search = request.GET.get("q", "").strip()

    plans = (
        GTMPlan.objects.for_workspace(workspace.id)
        .select_related("partner", "product")
        .order_by("partner__name", "-updated_at")
    )
    if status_filter and status_filter in dict(GTMPlanStatus.choices):
        plans = plans.filter(status=status_filter)
    if search:
        plans = plans.filter(name__icontains=search)

    partners = Partner.objects.for_workspace(workspace.id).filter(is_archived=False)

    # Group plans by partner for the table view
    grouped: dict = {}
    for plan in plans:
        grouped.setdefault(plan.partner, []).append(plan)

    context = {
        "workspace": workspace,
        "grouped_plans": grouped,
        "partners": partners,
        "status_filter": status_filter,
        "search": search,
        "status_choices": GTMPlanStatus.choices,
    }
    return render(request, "gtm/plan_list.html", context)


PLAN_TABS = [
    ("overview", "Overview"),
    ("audiences", "Audiences"),
    ("voice", "Voice"),
    ("value_props", "Value Props"),
    ("proof_points", "Proof"),
    ("do_say", "Do Say"),
    ("do_not_say", "Do Not Say"),
    ("cta_library", "CTAs"),
    ("competitors", "Competitors"),
    ("keywords_seo", "SEO"),
    ("compliance", "Compliance"),
    ("history", "History"),
    ("generations", "Generations"),
]


@require_workspace_role(ROLE_VIEW)
def plan_detail(request: HttpRequest, workspace_id, plan_id):
    workspace = request.workspace
    plan = get_object_or_404(
        GTMPlan.objects.for_workspace(workspace.id).select_related("partner", "product", "problem_solution"),
        id=plan_id,
    )
    active_tab = request.GET.get("tab", "overview")
    if active_tab not in dict(PLAN_TABS):
        active_tab = "overview"

    context = {
        "workspace": workspace,
        "plan": plan,
        "active_tab": active_tab,
        "tab_list": PLAN_TABS,
        "status_choices": GTMPlanStatus.choices,
    }
    return render(request, "gtm/plan_detail.html", context)


@require_workspace_role(ROLE_EDIT)
@require_http_methods(["GET", "POST"])
def plan_create(request: HttpRequest, workspace_id):
    workspace = request.workspace
    if request.method == "POST":
        form = gtm_forms.GTMPlanForm(request.POST)
        # Restrict partner choices to this workspace
        form.fields["partner"].queryset = Partner.objects.for_workspace(workspace.id)
        form.fields["product"].queryset = Product.objects.filter(partner__workspace=workspace)
        form.fields["problem_solution"].queryset = ProblemSolution.objects.filter(product__partner__workspace=workspace)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.workspace = workspace
            plan.created_by = request.user
            plan.last_edited_by = request.user
            plan.save()
            messages.success(request, f"Created plan: {plan.name}")
            return redirect("gtm:plan_detail", workspace_id=workspace.id, plan_id=plan.id)
    else:
        form = gtm_forms.GTMPlanForm()
        form.fields["partner"].queryset = Partner.objects.for_workspace(workspace.id)
        form.fields["product"].queryset = Product.objects.filter(partner__workspace=workspace)
        form.fields["problem_solution"].queryset = ProblemSolution.objects.filter(product__partner__workspace=workspace)

    return render(
        request,
        "gtm/plan_form.html",
        {"workspace": workspace, "form": form, "is_edit": False},
    )


SECTION_FORM_MAP = {
    "overview": gtm_forms.GTMPlanForm,
    "audiences": gtm_forms.AudiencesForm,
    "value_props": gtm_forms.ValuePropsForm,
    "proof_points": gtm_forms.ProofPointsForm,
    "voice": gtm_forms.VoiceForm,
    "do_say": gtm_forms.DoSayForm,
    "do_not_say": gtm_forms.DoNotSayForm,
    "competitors": gtm_forms.CompetitorsForm,
    "keywords_seo": gtm_forms.KeywordsForm,
    "cta_library": gtm_forms.CTALibraryForm,
    "compliance": gtm_forms.GTMPlanComplianceForm,
}

JSON_SECTIONS = {
    "audiences",
    "value_props",
    "proof_points",
    "voice",
    "do_say",
    "do_not_say",
    "competitors",
    "keywords_seo",
    "cta_library",
}


@require_workspace_role(ROLE_EDIT)
@require_http_methods(["GET", "POST"])
def plan_edit_section(request: HttpRequest, workspace_id, plan_id, section):
    workspace = request.workspace
    plan = get_object_or_404(GTMPlan.objects.for_workspace(workspace.id), id=plan_id)
    form_cls = SECTION_FORM_MAP.get(section)
    if not form_cls:
        return HttpResponse(status=404)

    if section in JSON_SECTIONS:
        if request.method == "POST":
            form = form_cls(request.POST)
            if form.is_valid():
                value = form.cleaned_data.get("raw_json", form_cls().empty_value())
                setattr(plan, section, value)
                plan.last_edited_by = request.user
                plan.save()
                return render(
                    request,
                    "gtm/partials/section_view.html",
                    {"plan": plan, "workspace": workspace, "section": section},
                )
        else:
            form = form_cls(initial_data=getattr(plan, section))
        return render(
            request,
            "gtm/partials/section_edit.html",
            {"workspace": workspace, "plan": plan, "form": form, "section": section},
        )

    # Non-JSON section forms operate directly on the model.
    if request.method == "POST":
        form = form_cls(request.POST, instance=plan)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.last_edited_by = request.user
            obj.save()
            return render(
                request,
                "gtm/partials/section_view.html",
                {"plan": plan, "workspace": workspace, "section": section},
            )
    else:
        form = form_cls(instance=plan)

    return render(
        request,
        "gtm/partials/section_edit.html",
        {"workspace": workspace, "plan": plan, "form": form, "section": section},
    )


@require_workspace_role(ROLE_ADMIN)
@require_POST
def plan_archive(request: HttpRequest, workspace_id, plan_id):
    workspace = request.workspace
    plan = get_object_or_404(GTMPlan.objects.for_workspace(workspace.id), id=plan_id)
    plan.status = GTMPlanStatus.ARCHIVED
    plan.last_edited_by = request.user
    plan.save()
    messages.success(request, f"Archived plan: {plan.name}")
    return redirect("gtm:plan_list", workspace_id=workspace.id)


@require_workspace_role(ROLE_VIEW)
def plan_history(request: HttpRequest, workspace_id, plan_id):
    workspace = request.workspace
    plan = get_object_or_404(GTMPlan.objects.for_workspace(workspace.id), id=plan_id)
    revisions = GTMPlanRevision.objects.filter(plan=plan).select_related("edited_by").order_by("-created_at")[:50]
    return render(
        request,
        "gtm/partials/history.html",
        {"plan": plan, "workspace": workspace, "revisions": revisions},
    )


# --------------------------------------------------------------------------
# Partner CRUD
# --------------------------------------------------------------------------


@require_workspace_role(ROLE_EDIT)
@require_http_methods(["GET", "POST"])
def partner_create(request: HttpRequest, workspace_id):
    workspace = request.workspace
    if request.method == "POST":
        form = gtm_forms.PartnerForm(request.POST)
        if form.is_valid():
            partner = form.save(commit=False)
            partner.workspace = workspace
            partner.save()
            messages.success(request, f"Added partner: {partner.name}")
            if request.htmx:
                return HttpResponse(
                    headers={"HX-Redirect": reverse("gtm:plan_list", kwargs={"workspace_id": workspace.id})}
                )
            return redirect("gtm:plan_list", workspace_id=workspace.id)
    else:
        form = gtm_forms.PartnerForm()
    return render(
        request,
        "gtm/partials/partner_form.html",
        {"workspace": workspace, "form": form, "is_edit": False},
    )


@require_workspace_role(ROLE_EDIT)
@require_http_methods(["GET", "POST"])
def partner_edit(request: HttpRequest, workspace_id, partner_id):
    workspace = request.workspace
    partner = get_object_or_404(Partner.objects.for_workspace(workspace.id), id=partner_id)
    if request.method == "POST":
        form = gtm_forms.PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated partner: {partner.name}")
            return render(
                request,
                "gtm/partials/partner_card.html",
                {"partner": partner, "workspace": workspace},
            )
    else:
        form = gtm_forms.PartnerForm(instance=partner)
    return render(
        request,
        "gtm/partials/partner_form.html",
        {"workspace": workspace, "form": form, "partner": partner, "is_edit": True},
    )


@require_workspace_role(ROLE_ADMIN)
@require_POST
def partner_archive(request: HttpRequest, workspace_id, partner_id):
    workspace = request.workspace
    partner = get_object_or_404(Partner.objects.for_workspace(workspace.id), id=partner_id)
    partner.is_archived = True
    partner.save()
    messages.success(request, f"Archived partner: {partner.name}")
    return redirect("gtm:plan_list", workspace_id=workspace.id)


# --------------------------------------------------------------------------
# Product CRUD
# --------------------------------------------------------------------------


@require_workspace_role(ROLE_EDIT)
@require_http_methods(["GET", "POST"])
def product_create(request: HttpRequest, workspace_id):
    workspace = request.workspace
    if request.method == "POST":
        form = gtm_forms.ProductForm(request.POST)
        form.fields["partner"].queryset = Partner.objects.for_workspace(workspace.id)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Added product: {product.name}")
            return redirect("gtm:plan_list", workspace_id=workspace.id)
    else:
        form = gtm_forms.ProductForm()
        form.fields["partner"].queryset = Partner.objects.for_workspace(workspace.id)
    return render(
        request,
        "gtm/partials/product_form.html",
        {"workspace": workspace, "form": form, "is_edit": False},
    )


@require_workspace_role(ROLE_EDIT)
@require_http_methods(["GET", "POST"])
def product_edit(request: HttpRequest, workspace_id, product_id):
    workspace = request.workspace
    product = get_object_or_404(Product.objects.filter(partner__workspace=workspace), id=product_id)
    if request.method == "POST":
        form = gtm_forms.ProductForm(request.POST, instance=product)
        form.fields["partner"].queryset = Partner.objects.for_workspace(workspace.id)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated product: {product.name}")
            return redirect("gtm:plan_list", workspace_id=workspace.id)
    else:
        form = gtm_forms.ProductForm(instance=product)
        form.fields["partner"].queryset = Partner.objects.for_workspace(workspace.id)
    return render(
        request,
        "gtm/partials/product_form.html",
        {"workspace": workspace, "form": form, "product": product, "is_edit": True},
    )


@require_workspace_role(ROLE_ADMIN)
@require_POST
def product_archive(request: HttpRequest, workspace_id, product_id):
    workspace = request.workspace
    product = get_object_or_404(Product.objects.filter(partner__workspace=workspace), id=product_id)
    product.is_archived = True
    product.save()
    messages.success(request, f"Archived product: {product.name}")
    return redirect("gtm:plan_list", workspace_id=workspace.id)


# --------------------------------------------------------------------------
# ProblemSolution CRUD
# --------------------------------------------------------------------------


@require_workspace_role(ROLE_EDIT)
@require_http_methods(["GET", "POST"])
def problem_solution_create(request: HttpRequest, workspace_id):
    workspace = request.workspace
    if request.method == "POST":
        form = gtm_forms.ProblemSolutionForm(request.POST)
        form.fields["product"].queryset = Product.objects.filter(partner__workspace=workspace)
        if form.is_valid():
            ps = form.save()
            messages.success(request, f"Added problem/solution: {ps.target_persona}")
            return redirect("gtm:plan_list", workspace_id=workspace.id)
    else:
        form = gtm_forms.ProblemSolutionForm()
        form.fields["product"].queryset = Product.objects.filter(partner__workspace=workspace)
    return render(
        request,
        "gtm/partials/problem_solution_form.html",
        {"workspace": workspace, "form": form, "is_edit": False},
    )


@require_workspace_role(ROLE_EDIT)
@require_http_methods(["GET", "POST"])
def problem_solution_edit(request: HttpRequest, workspace_id, ps_id):
    workspace = request.workspace
    ps = get_object_or_404(
        ProblemSolution.objects.filter(product__partner__workspace=workspace),
        id=ps_id,
    )
    if request.method == "POST":
        form = gtm_forms.ProblemSolutionForm(request.POST, instance=ps)
        form.fields["product"].queryset = Product.objects.filter(partner__workspace=workspace)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated: {ps.target_persona}")
            return redirect("gtm:plan_list", workspace_id=workspace.id)
    else:
        form = gtm_forms.ProblemSolutionForm(instance=ps)
        form.fields["product"].queryset = Product.objects.filter(partner__workspace=workspace)
    return render(
        request,
        "gtm/partials/problem_solution_form.html",
        {"workspace": workspace, "form": form, "ps": ps, "is_edit": True},
    )


@require_workspace_role(ROLE_ADMIN)
@require_POST
def problem_solution_delete(request: HttpRequest, workspace_id, ps_id):
    workspace = request.workspace
    ps = get_object_or_404(
        ProblemSolution.objects.filter(product__partner__workspace=workspace),
        id=ps_id,
    )
    ps.delete()
    messages.success(request, "Deleted problem/solution")
    return redirect("gtm:plan_list", workspace_id=workspace.id)
