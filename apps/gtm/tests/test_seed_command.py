"""Tests for the seed_oneclaw_gtm management command."""

from __future__ import annotations

import io

import pytest
from django.core.management import CommandError, call_command

from apps.gtm.models import GTMPlan, Partner, Product


@pytest.mark.django_db
class TestSeedCommand:
    def test_no_workspaces_raises(self):
        with pytest.raises(CommandError, match="No workspaces"):
            call_command("seed_oneclaw_gtm")

    def test_invalid_workspace_id_raises(self, workspace):
        with pytest.raises(CommandError, match="not found"):
            call_command(
                "seed_oneclaw_gtm",
                workspace_id="00000000-0000-0000-0000-000000000000",
            )

    def test_seeds_partner_products_and_plans(self, workspace):
        out = io.StringIO()
        call_command("seed_oneclaw_gtm", workspace_id=str(workspace.id), stdout=out)

        partner = Partner.objects.get(workspace=workspace, slug="1claw")
        assert partner.name == "1Claw"

        products = Product.objects.filter(partner=partner)
        assert products.count() == 3
        assert {p.slug for p in products} == {"shroud", "intents", "vault"}

        plans = GTMPlan.objects.for_workspace(workspace.id)
        assert plans.count() == 3
        # Every plan should have value_props populated
        for plan in plans:
            assert len(plan.value_props) > 0
            assert len(plan.do_not_say) > 0

    def test_idempotent_rerun(self, workspace):
        call_command("seed_oneclaw_gtm", workspace_id=str(workspace.id), stdout=io.StringIO())
        first_count = GTMPlan.objects.for_workspace(workspace.id).count()
        call_command("seed_oneclaw_gtm", workspace_id=str(workspace.id), stdout=io.StringIO())
        second_count = GTMPlan.objects.for_workspace(workspace.id).count()
        assert first_count == second_count == 3

    def test_does_not_overwrite_user_edits(self, workspace):
        call_command("seed_oneclaw_gtm", workspace_id=str(workspace.id), stdout=io.StringIO())
        plan = GTMPlan.objects.get(workspace=workspace, slug="shroud-plan")
        plan.compliance_notes = "User-customized note"
        plan.save()

        call_command("seed_oneclaw_gtm", workspace_id=str(workspace.id), stdout=io.StringIO())
        plan.refresh_from_db()
        assert plan.compliance_notes == "User-customized note"

    def test_demo_content_flag_creates_stub_generations(self, workspace):
        from apps.ai.models import AIGeneration

        out = io.StringIO()
        call_command(
            "seed_oneclaw_gtm",
            workspace_id=str(workspace.id),
            demo_content=True,
            stdout=out,
        )
        # 3 plans × 10 stubbed generations each = 30
        assert AIGeneration.objects.for_workspace(workspace.id).count() == 30
        assert "Seeded 30 stubbed AIGenerations" in out.getvalue()

    def test_uses_first_workspace_when_no_id(self, workspace):
        # Existing fixture creates `workspace` already
        call_command("seed_oneclaw_gtm", stdout=io.StringIO())
        assert Partner.objects.filter(workspace=workspace).count() == 1
