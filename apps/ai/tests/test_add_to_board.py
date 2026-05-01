"""Tests for the idea_seed → Kanban board converter."""

from __future__ import annotations

import json

import pytest
from django.test import Client
from django.urls import reverse

from apps.ai.models import AIGeneration, GenerationKind, GenerationStatus


@pytest.fixture
def client_logged_in(db, user):
    c = Client()
    c.force_login(user)
    return c


def _idea_seed_gen(workspace, status=GenerationStatus.SUCCEEDED, plan=None):
    payload = {
        "ideas": [
            {
                "title": "First idea",
                "description": "Why agents need vault-aware redaction",
                "target_audience": "Sec eng",
                "cta": "Read docs",
                "suggested_platforms": ["twitter", "linkedin_personal"],
            },
            {
                "title": "Second idea",
                "description": "MPC across three clouds",
                "target_audience": "CISO",
                "suggested_platforms": ["linkedin_personal"],
            },
        ]
    }
    return AIGeneration.objects.create(
        workspace=workspace,
        gtm_plan=plan,
        kind=GenerationKind.IDEA_SEED,
        provider="stub",
        model="x",
        status=status,
        output_payload={"text": json.dumps(payload)},
    )


@pytest.mark.django_db
class TestAddIdeasToBoard:
    def test_creates_idea_rows(self, client_logged_in, workspace, owner_membership, plan):
        from apps.composer.models import Idea

        gen = _idea_seed_gen(workspace, plan=plan)
        resp = client_logged_in.post(
            reverse(
                "ai:add_ideas_to_board",
                kwargs={"workspace_id": workspace.id, "generation_id": gen.id},
            )
        )
        assert resp.status_code == 200
        ideas = Idea.objects.filter(workspace=workspace).order_by("position")
        assert ideas.count() == 2
        assert ideas[0].title == "First idea"
        assert "ai-generated" in ideas[0].tags
        assert any(t.startswith("plan:") for t in ideas[0].tags)
        assert "twitter" in ideas[0].tags

    def test_rejects_wrong_kind(self, client_logged_in, workspace, owner_membership):
        gen = AIGeneration.objects.create(
            workspace=workspace,
            kind=GenerationKind.CAPTION,
            provider="stub",
            model="x",
            status=GenerationStatus.SUCCEEDED,
            output_payload={"text": "{}"},
        )
        resp = client_logged_in.post(
            reverse(
                "ai:add_ideas_to_board",
                kwargs={"workspace_id": workspace.id, "generation_id": gen.id},
            )
        )
        assert resp.status_code == 400

    def test_rejects_pending(self, client_logged_in, workspace, owner_membership):
        gen = _idea_seed_gen(workspace, status=GenerationStatus.RUNNING)
        resp = client_logged_in.post(
            reverse(
                "ai:add_ideas_to_board",
                kwargs={"workspace_id": workspace.id, "generation_id": gen.id},
            )
        )
        assert resp.status_code == 400

    def test_creates_default_group_if_none(self, client_logged_in, workspace, owner_membership):
        from apps.composer.models import IdeaGroup

        gen = _idea_seed_gen(workspace)
        assert IdeaGroup.objects.for_workspace(workspace.id).count() == 0
        client_logged_in.post(
            reverse(
                "ai:add_ideas_to_board",
                kwargs={"workspace_id": workspace.id, "generation_id": gen.id},
            )
        )
        assert IdeaGroup.objects.for_workspace(workspace.id).count() == 1

    def test_viewer_denied(self, client_logged_in, workspace, viewer_membership):
        gen = _idea_seed_gen(workspace)
        resp = client_logged_in.post(
            reverse(
                "ai:add_ideas_to_board",
                kwargs={"workspace_id": workspace.id, "generation_id": gen.id},
            )
        )
        assert resp.status_code == 403
