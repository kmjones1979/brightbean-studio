"""Shared fixtures for AI app tests."""

from __future__ import annotations

import pytest
from django.utils import timezone


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="ai-tester@example.com",
        password="pass1234",
        name="Tester",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="AI Test Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="AI Test Workspace", organization=organization)


def _make_member(user, workspace, role):
    from apps.members.models import OrgMembership, WorkspaceMembership

    OrgMembership.objects.get_or_create(
        user=user,
        organization=workspace.organization,
        defaults={"org_role": OrgMembership.OrgRole.MEMBER},
    )
    return WorkspaceMembership.objects.create(user=user, workspace=workspace, workspace_role=role)


@pytest.fixture
def owner_membership(db, user, workspace):
    return _make_member(user, workspace, "owner")


@pytest.fixture
def manager_membership(db, user, workspace):
    return _make_member(user, workspace, "manager")


@pytest.fixture
def viewer_membership(db, user, workspace):
    return _make_member(user, workspace, "viewer")


@pytest.fixture
def plan(db, workspace):
    """A simple GTMPlan fixture for AI tests that need one."""
    from apps.gtm.models import GTMPlan, Partner

    partner = Partner.objects.create(workspace=workspace, name="1Claw")
    return GTMPlan.objects.create(
        workspace=workspace,
        partner=partner,
        name="Shroud test plan",
    )
