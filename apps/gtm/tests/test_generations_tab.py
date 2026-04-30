"""Phase 5: Generations tab on the plan detail page."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse


@pytest.fixture
def client_logged_in(db, user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
class TestGenerationsTab:
    def test_empty_state(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.get(
            reverse("gtm:plan_detail", kwargs={"workspace_id": workspace.id, "plan_id": plan.id}) + "?tab=generations"
        )
        assert resp.status_code == 200
        assert b"No AI generations yet" in resp.content
        assert b"Compose with AI" in resp.content

    def test_lists_generations_referencing_this_plan(self, client_logged_in, workspace, owner_membership, plan):
        from apps.ai.models import AIGeneration, GenerationKind, GenerationStatus

        AIGeneration.objects.create(
            workspace=workspace,
            gtm_plan=plan,
            kind=GenerationKind.CAPTION,
            provider="anthropic",
            model="claude-sonnet-4-6",
            status=GenerationStatus.SUCCEEDED,
            cost_usd_micro=2_000,
        )
        AIGeneration.objects.create(
            workspace=workspace,
            gtm_plan=plan,
            kind=GenerationKind.HOOK,
            provider="anthropic",
            model="claude-sonnet-4-6",
            status=GenerationStatus.FAILED,
        )
        resp = client_logged_in.get(
            reverse("gtm:plan_detail", kwargs={"workspace_id": workspace.id, "plan_id": plan.id}) + "?tab=generations"
        )
        assert resp.status_code == 200
        body = resp.content.decode()
        assert "caption" in body
        assert "hook" in body
        assert "Succeeded" in body
        assert "Failed" in body

    def test_does_not_leak_other_plans_generations(self, client_logged_in, workspace, owner_membership, plan, partner):
        from apps.ai.models import AIGeneration, GenerationKind, GenerationStatus
        from apps.gtm.models import GTMPlan

        other_plan = GTMPlan.objects.create(
            workspace=workspace,
            partner=partner,
            name="Other plan",
        )
        AIGeneration.objects.create(
            workspace=workspace,
            gtm_plan=other_plan,
            kind=GenerationKind.CAPTION,
            provider="anthropic",
            model="x",
            status=GenerationStatus.SUCCEEDED,
        )
        resp = client_logged_in.get(
            reverse("gtm:plan_detail", kwargs={"workspace_id": workspace.id, "plan_id": plan.id}) + "?tab=generations"
        )
        assert resp.status_code == 200
        # The plan being viewed has no generations attached, so empty state should show
        assert b"No AI generations yet" in resp.content
