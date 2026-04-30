"""Tests for the AI workspace settings view."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.ai.models import AIWorkspaceConfig


@pytest.fixture
def client_logged_in(db, user):
    c = Client()
    c.force_login(user)
    return c


def _settings_url(workspace):
    return reverse("ai:settings", kwargs={"workspace_id": workspace.id})


@pytest.mark.django_db
class TestSettingsPage:
    def test_manager_can_view(self, client_logged_in, workspace, manager_membership):
        resp = client_logged_in.get(_settings_url(workspace))
        assert resp.status_code == 200
        assert b"AI Settings" in resp.content

    def test_owner_can_view(self, client_logged_in, workspace, owner_membership):
        resp = client_logged_in.get(_settings_url(workspace))
        assert resp.status_code == 200

    def test_viewer_denied(self, client_logged_in, workspace, viewer_membership):
        resp = client_logged_in.get(_settings_url(workspace))
        assert resp.status_code == 403

    def test_post_updates_config(self, client_logged_in, workspace, owner_membership):
        resp = client_logged_in.post(
            _settings_url(workspace),
            {
                "default_model": "claude-haiku-4-5",
                "monthly_usd_cap": "50",
                "shroud_agent_id": "agent_x",
            },
        )
        assert resp.status_code in (200, 302)
        config = AIWorkspaceConfig.objects.get(workspace=workspace)
        assert config.default_model == "claude-haiku-4-5"
        assert config.monthly_usd_cap == 50
        assert config.shroud_agent_id == "agent_x"

    def test_get_creates_config_if_missing(self, client_logged_in, workspace, owner_membership):
        assert not AIWorkspaceConfig.objects.filter(workspace=workspace).exists()
        client_logged_in.get(_settings_url(workspace))
        assert AIWorkspaceConfig.objects.filter(workspace=workspace).exists()
