"""Tests for section editing flows (HTMX-style inline edits)."""

from __future__ import annotations

import json

import pytest
from django.test import Client
from django.urls import reverse


@pytest.fixture
def client_logged_in(db, user):
    c = Client()
    c.force_login(user)
    return c


def _section_url(workspace, plan, section):
    return reverse(
        "gtm:plan_edit_section",
        kwargs={
            "workspace_id": workspace.id,
            "plan_id": plan.id,
            "section": section,
        },
    )


@pytest.mark.django_db
class TestJSONSectionEdit:
    def test_get_returns_form(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.get(_section_url(workspace, plan, "value_props"))
        assert resp.status_code == 200
        assert b"raw_json" in resp.content

    def test_post_updates_value_props(self, client_logged_in, workspace, owner_membership, plan):
        payload = json.dumps(["A", "B", "C"])
        resp = client_logged_in.post(
            _section_url(workspace, plan, "value_props"),
            {"raw_json": payload},
        )
        assert resp.status_code == 200
        plan.refresh_from_db()
        assert plan.value_props == ["A", "B", "C"]

    def test_post_invalid_json_shows_error(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.post(
            _section_url(workspace, plan, "value_props"),
            {"raw_json": "not json"},
        )
        assert resp.status_code == 200
        assert b"Invalid JSON" in resp.content

    def test_unknown_section_404(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.get(_section_url(workspace, plan, "bogus"))
        assert resp.status_code == 404

    def test_voice_empty_value_is_dict(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.post(
            _section_url(workspace, plan, "voice"),
            {"raw_json": ""},
        )
        assert resp.status_code == 200
        plan.refresh_from_db()
        assert plan.voice == {}

    def test_compliance_uses_model_form(self, client_logged_in, workspace, owner_membership, plan):
        resp = client_logged_in.post(
            _section_url(workspace, plan, "compliance"),
            {"compliance_notes": "SOC 2 Type I in progress"},
        )
        assert resp.status_code == 200
        plan.refresh_from_db()
        assert plan.compliance_notes == "SOC 2 Type I in progress"

    def test_viewer_denied(self, client_logged_in, workspace, viewer_membership, plan):
        resp = client_logged_in.get(_section_url(workspace, plan, "value_props"))
        assert resp.status_code == 403


@pytest.mark.django_db
class TestPlanHistory:
    def test_history_view(self, client_logged_in, workspace, owner_membership, plan):
        plan.value_props = ["v1"]
        plan.save()
        resp = client_logged_in.get(
            reverse(
                "gtm:plan_history",
                kwargs={"workspace_id": workspace.id, "plan_id": plan.id},
            )
        )
        assert resp.status_code == 200
        assert b"value_props" in resp.content
