"""Tests for GTM models — slug generation, scoping, constraints."""

from __future__ import annotations

import pytest

from apps.gtm.models import (
    GTMPlan,
    GTMPlanStatus,
    Partner,
    ProblemSolution,
    Product,
)


@pytest.mark.django_db
class TestPartner:
    def test_create_with_auto_slug(self, workspace):
        partner = Partner.objects.create(workspace=workspace, name="My Cool Co")
        assert partner.slug == "my-cool-co"

    def test_str(self, partner):
        assert str(partner) == "1Claw"

    def test_workspace_scope_isolation(self, workspace, other_workspace):
        Partner.objects.create(workspace=workspace, name="A")
        Partner.objects.create(workspace=other_workspace, name="B")
        assert Partner.objects.for_workspace(workspace.id).count() == 1
        assert Partner.objects.for_workspace(other_workspace.id).count() == 1


@pytest.mark.django_db
class TestProduct:
    def test_create_with_auto_slug(self, partner):
        product = Product.objects.create(partner=partner, name="Vault")
        assert product.slug == "vault"

    def test_str(self, product):
        assert str(product) == "1Claw / Shroud"


@pytest.mark.django_db
class TestProblemSolution:
    def test_one_primary_per_product_constraint(self, product):
        ProblemSolution.objects.create(
            product=product,
            problem_statement="P1",
            solution_statement="S1",
            target_persona="CISO",
            is_primary=True,
        )
        from django.db import IntegrityError, transaction

        with pytest.raises(IntegrityError), transaction.atomic():
            ProblemSolution.objects.create(
                product=product,
                problem_statement="P2",
                solution_statement="S2",
                target_persona="VP Eng",
                is_primary=True,
            )

    def test_multiple_non_primary_allowed(self, product):
        ProblemSolution.objects.create(
            product=product,
            problem_statement="P1",
            solution_statement="S1",
            target_persona="A",
            is_primary=False,
        )
        ProblemSolution.objects.create(
            product=product,
            problem_statement="P2",
            solution_statement="S2",
            target_persona="B",
            is_primary=False,
        )
        assert ProblemSolution.objects.filter(product=product).count() == 2


@pytest.mark.django_db
class TestGTMPlan:
    def test_default_status_draft(self, plan):
        assert plan.status == GTMPlanStatus.DRAFT
        assert not plan.is_archived

    def test_archive_flag(self, plan):
        plan.status = GTMPlanStatus.ARCHIVED
        plan.save()
        assert plan.is_archived

    def test_str(self, plan):
        assert str(plan) == "Shroud — Security teams"

    def test_slug_autopopulated(self, workspace, partner):
        plan = GTMPlan.objects.create(workspace=workspace, partner=partner, name="My Cool Plan")
        assert plan.slug == "my-cool-plan"

    def test_workspace_scope_isolation(self, workspace, other_workspace, partner, user):
        # Other workspace needs its own partner
        other_partner = Partner.objects.create(workspace=other_workspace, name="OtherCorp")
        GTMPlan.objects.create(workspace=workspace, partner=partner, name="A")
        GTMPlan.objects.create(workspace=other_workspace, partner=other_partner, name="B")
        assert GTMPlan.objects.for_workspace(workspace.id).count() == 1
        assert GTMPlan.objects.for_workspace(other_workspace.id).count() == 1

    def test_partner_protect_on_delete(self, plan, partner):
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError):
            partner.delete()

    def test_default_json_fields_are_empty(self, plan):
        assert plan.audiences == []
        assert plan.value_props == []
        assert plan.proof_points == []
        assert plan.voice == {}
        assert plan.do_say == []
        assert plan.do_not_say == []
