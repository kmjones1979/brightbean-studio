"""End-to-end tests for the Phase 3 generation flow.

Background task is patched so test execution is synchronous and we don't need
the worker container running.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.ai.models import AIGeneration, GenerationKind, GenerationStatus


@pytest.fixture
def client_logged_in(db, user):
    c = Client()
    c.force_login(user)
    return c


def _url(name, workspace, **kwargs):
    return reverse(f"ai:{name}", kwargs={"workspace_id": workspace.id, **kwargs})


@pytest.mark.django_db
class TestGenerateCaption:
    def test_editor_can_queue(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(
                _url("generate_caption", workspace),
                {"brief": "Announce MCP", "platform": "twitter"},
            )
        assert resp.status_code == 200
        gen = AIGeneration.objects.for_workspace(workspace.id).first()
        assert gen.kind == GenerationKind.CAPTION
        assert gen.status == GenerationStatus.QUEUED
        assert gen.input_payload["brief"] == "Announce MCP"
        assert gen.input_payload["platform"] == "twitter"

    def test_viewer_denied(self, client_logged_in, workspace, viewer_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(
                _url("generate_caption", workspace),
                {"brief": "x", "platform": "twitter"},
            )
        assert resp.status_code == 403

    def test_empty_brief_400(self, client_logged_in, workspace, owner_membership):
        resp = client_logged_in.post(
            _url("generate_caption", workspace),
            {"brief": "", "platform": "twitter"},
        )
        assert resp.status_code == 400

    def test_unknown_platform_400(self, client_logged_in, workspace, owner_membership):
        resp = client_logged_in.post(
            _url("generate_caption", workspace),
            {"brief": "x", "platform": "myspace"},
        )
        assert resp.status_code == 400

    def test_cap_exceeded_returns_429(self, client_logged_in, workspace, owner_membership):
        from apps.ai.models import AIWorkspaceConfig

        AIWorkspaceConfig.objects.create(
            workspace=workspace,
            monthly_usd_cap=1,
            current_month_spend_micro=2_000_000,
        )
        resp = client_logged_in.post(
            _url("generate_caption", workspace),
            {"brief": "x", "platform": "twitter"},
        )
        assert resp.status_code == 429


@pytest.mark.django_db
class TestGenerateMultiPlatform:
    def test_queues_one_generation(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(
                _url("generate_multi_platform", workspace),
                {"brief": "Launch", "platforms[]": ["twitter", "linkedin_personal"]},
            )
        assert resp.status_code == 200
        gen = AIGeneration.objects.for_workspace(workspace.id).first()
        assert gen.kind == GenerationKind.MULTI_PLATFORM
        assert gen.input_payload["platforms"] == ["twitter", "linkedin_personal"]

    def test_no_platforms_400(self, client_logged_in, workspace, owner_membership):
        resp = client_logged_in.post(
            _url("generate_multi_platform", workspace),
            {"brief": "x"},
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestGenerationPoll:
    def test_pending_returns_pending_partial(self, client_logged_in, workspace, owner_membership):
        gen = AIGeneration.objects.create(
            workspace=workspace,
            kind=GenerationKind.CAPTION,
            provider="anthropic",
            model="claude-sonnet-4-6",
            status=GenerationStatus.RUNNING,
        )
        resp = client_logged_in.get(_url("generation_poll", workspace, generation_id=gen.id))
        assert resp.status_code == 200
        # Pending partial includes the polling hx-trigger
        assert b"hx-trigger" in resp.content

    def test_succeeded_returns_result_partial(self, client_logged_in, workspace, owner_membership):
        gen = AIGeneration.objects.create(
            workspace=workspace,
            kind=GenerationKind.CAPTION,
            provider="anthropic",
            model="claude-sonnet-4-6",
            status=GenerationStatus.SUCCEEDED,
            output_payload={"text": '{"variants":[{"text":"hello","char_count":5,"rationale":"r"}]}'},
        )
        resp = client_logged_in.get(_url("generation_poll", workspace, generation_id=gen.id))
        assert resp.status_code == 200
        assert b"hello" in resp.content
        # Should NOT include the polling trigger
        assert b"every 1s" not in resp.content


@pytest.mark.django_db
class TestGeneratePanel:
    def test_panel_renders(self, client_logged_in, workspace, owner_membership):
        resp = client_logged_in.get(_url("generate_panel", workspace))
        assert resp.status_code == 200
        assert b"AI Compose" in resp.content
        assert b"GTM plan" in resp.content
