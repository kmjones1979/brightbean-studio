from django.urls import path

from apps.gtm import views

app_name = "gtm"

urlpatterns = [
    # Plan list & detail
    path("", views.plan_list, name="plan_list"),
    path("new/", views.plan_create, name="plan_create"),
    path("<uuid:plan_id>/", views.plan_detail, name="plan_detail"),
    path("<uuid:plan_id>/edit/<str:section>/", views.plan_edit_section, name="plan_edit_section"),
    path("<uuid:plan_id>/archive/", views.plan_archive, name="plan_archive"),
    path("<uuid:plan_id>/history/", views.plan_history, name="plan_history"),
    # Partner CRUD (HTMX modal partials)
    path("partners/new/", views.partner_create, name="partner_create"),
    path("partners/<uuid:partner_id>/edit/", views.partner_edit, name="partner_edit"),
    path("partners/<uuid:partner_id>/archive/", views.partner_archive, name="partner_archive"),
    # Product CRUD
    path("products/new/", views.product_create, name="product_create"),
    path("products/<uuid:product_id>/edit/", views.product_edit, name="product_edit"),
    path("products/<uuid:product_id>/archive/", views.product_archive, name="product_archive"),
    # ProblemSolution CRUD
    path("problem-solutions/new/", views.problem_solution_create, name="problem_solution_create"),
    path(
        "problem-solutions/<uuid:ps_id>/edit/",
        views.problem_solution_edit,
        name="problem_solution_edit",
    ),
    path(
        "problem-solutions/<uuid:ps_id>/delete/",
        views.problem_solution_delete,
        name="problem_solution_delete",
    ),
]
