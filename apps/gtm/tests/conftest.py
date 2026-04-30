"""Shared pytest fixtures for the GTM test suite."""

from __future__ import annotations

import pytest
from django.utils import timezone


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="kev@example.com",
        password="pass1234",
        name="Kev",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def other_user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="rival@example.com",
        password="pass1234",
        name="Rival",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Test Org")


@pytest.fixture
def other_organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Other Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Primary Workspace", organization=organization)


@pytest.fixture
def other_workspace(db, other_organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Other Workspace", organization=other_organization)


@pytest.fixture
def org_membership(db, user, organization):
    from apps.members.models import OrgMembership

    return OrgMembership.objects.create(
        user=user,
        organization=organization,
        org_role=OrgMembership.OrgRole.OWNER,
    )


def _make_member(user, workspace, role):
    from apps.members.models import OrgMembership, WorkspaceMembership

    OrgMembership.objects.get_or_create(
        user=user,
        organization=workspace.organization,
        defaults={"org_role": OrgMembership.OrgRole.MEMBER},
    )
    return WorkspaceMembership.objects.create(
        user=user,
        workspace=workspace,
        workspace_role=role,
    )


@pytest.fixture
def owner_membership(db, user, workspace):
    return _make_member(user, workspace, "owner")


@pytest.fixture
def editor_membership(db, user, workspace):
    return _make_member(user, workspace, "editor")


@pytest.fixture
def viewer_membership(db, user, workspace):
    return _make_member(user, workspace, "viewer")


@pytest.fixture
def partner(db, workspace):
    from apps.gtm.models import Partner

    return Partner.objects.create(workspace=workspace, name="1Claw")


@pytest.fixture
def product(db, partner):
    from apps.gtm.models import Product

    return Product.objects.create(partner=partner, name="Shroud")


@pytest.fixture
def plan(db, workspace, partner, product, user):
    from apps.gtm.models import GTMPlan

    return GTMPlan.objects.create(
        workspace=workspace,
        partner=partner,
        product=product,
        name="Shroud — Security teams",
        created_by=user,
    )
