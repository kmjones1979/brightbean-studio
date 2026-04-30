"""View-level tests for the GTM app — RBAC matrix and basic flows."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.gtm.models import GTMPlan, GTMPlanStatus, Partner


@pytest.fixture
def client_logged_in(db, user):
    c = Client()
    c.force_login(user)
    return c


def _url(name, workspace, **kwargs):
    return reverse(f"gtm:{name}", kwargs={"workspace_id": workspace.id, **kwargs})


@pytest.mark.django_db
class TestPlanListAccess:
    def test_viewer_can_read(self, client_logged_in, workspace, viewer_membership):
        resp = client_logged_in.get(_url("plan_list", workspace))
        assert resp.status_code == 200

    def test_editor_can_read(self, client_logged_in, workspace, editor_membership):
        resp = client_logged_in.get(_url("plan_list", workspace))
        assert resp.status_code == 200

    def test_non_member_denied(self, client_logged_in, workspace):
        resp = client_logged_in.get(_url("plan_list", workspace))
        assert resp.status_code == 403

    def test_search_filter(
        self,
        client_logged_in,
        workspace,
        owner_membership,
        partner,
    ):
        GTMPlan.objects.create(workspace=workspace, partner=partner, name="Alpha")
        GTMPlan.objects.create(workspace=workspace, partner=partner, name="Beta")
        resp = client_logged_in.get(_url("plan_list", workspace) + "?q=Alpha")
        assert resp.status_code == 200
        body = resp.content.decode()
        assert "Alpha" in body
        assert "Beta" not in body


@pytest.mark.django_db
class TestPlanCreate:
    def test_viewer_cannot_create(self, client_logged_in, workspace, viewer_membership, partner):
        resp = client_logged_in.post(
            _url("plan_create", workspace),
            {
                "name": "X",
                "status": GTMPlanStatus.DRAFT,
                "partner": str(partner.id),
                "product": "",
                "problem_solution": "",
            },
        )
        assert resp.status_code == 403
        assert GTMPlan.objects.count() == 0

    def test_editor_can_create(self, client_logged_in, workspace, editor_membership, partner):
        resp = client_logged_in.post(
            _url("plan_create", workspace),
            {
                "name": "Editor Plan",
                "status": GTMPlanStatus.DRAFT,
                "partner": str(partner.id),
                "product": "",
                "problem_solution": "",
            },
        )
        assert resp.status_code in (200, 302)
        assert GTMPlan.objects.filter(name="Editor Plan").exists()


@pytest.mark.django_db
class TestPlanArchive:
    def test_viewer_cannot_archive(self, client_logged_in, workspace, viewer_membership, plan):
        resp = client_logged_in.post(_url("plan_archive", workspace, plan_id=plan.id))
        assert resp.status_code == 403
        plan.refresh_from_db()
        assert plan.status != GTMPlanStatus.ARCHIVED

    def test_editor_cannot_archive(self, client_logged_in, workspace, editor_membership, plan):
        # editor < manager => denied
        resp = client_logged_in.post(_url("plan_archive", workspace, plan_id=plan.id))
        assert resp.status_code == 403

    def test_owner_can_archive(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.post(_url("plan_archive", workspace, plan_id=plan.id))
        assert resp.status_code in (200, 302)
        plan.refresh_from_db()
        assert plan.status == GTMPlanStatus.ARCHIVED


@pytest.mark.django_db
class TestPartnerCreate:
    def test_editor_can_create(self, client_logged_in, workspace, editor_membership):
        resp = client_logged_in.post(
            _url("partner_create", workspace),
            {"name": "NewCorp", "website": "", "notes": ""},
        )
        assert resp.status_code in (200, 302)
        assert Partner.objects.filter(name="NewCorp").exists()

    def test_viewer_cannot_create(self, client_logged_in, workspace, viewer_membership):
        resp = client_logged_in.post(
            _url("partner_create", workspace),
            {"name": "Nope"},
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestPlanDetail:
    def test_loads_overview_tab_by_default(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.get(_url("plan_detail", workspace, plan_id=plan.id))
        assert resp.status_code == 200
        assert b"Shroud" in resp.content

    def test_invalid_tab_falls_back_to_overview(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.get(_url("plan_detail", workspace, plan_id=plan.id) + "?tab=bogus")
        assert resp.status_code == 200

    def test_other_workspace_plan_404(
        self,
        client_logged_in,
        workspace,
        other_workspace,
        owner_membership,
        plan,
    ):
        # Plan exists in `workspace`. URL with `other_workspace.id` should 403
        # via RBAC (user not a member of other_workspace).
        resp = client_logged_in.get(
            reverse(
                "gtm:plan_detail",
                kwargs={"workspace_id": other_workspace.id, "plan_id": plan.id},
            )
        )
        assert resp.status_code == 403
