"""Smoke tests for Phase 4 generation kinds — endpoint routing, validation,
prompt rendering, and schema completeness.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.ai.models import AIGeneration, GenerationKind
from apps.ai.prompts import SCHEMAS, render_prompt


@pytest.fixture
def client_logged_in(db, user):
    c = Client()
    c.force_login(user)
    return c


def _url(name, workspace, **kwargs):
    return reverse(f"ai:{name}", kwargs={"workspace_id": workspace.id, **kwargs})


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind",
    [
        "caption",
        "multi_platform",
        "hook",
        "cta",
        "hashtags",
        "brief_expand",
        "idea_seed",
        "reply_draft",
    ],
)
def test_schema_present(kind):
    schema = SCHEMAS.get(kind)
    assert schema is not None
    assert schema["type"] == "object"


# -----------------------------------------------------------------------------
# Prompt rendering for new kinds
# -----------------------------------------------------------------------------


@pytest.fixture
def plan(db, workspace):
    from apps.gtm.models import GTMPlan, Partner, Product

    partner = Partner.objects.create(workspace=workspace, name="1Claw")
    product = Product.objects.create(partner=partner, name="Shroud")
    return GTMPlan.objects.create(
        workspace=workspace,
        partner=partner,
        product=product,
        name="Shroud plan",
        value_props=["Vault-aware redaction"],
        proof_points=[{"claim": "AMD SEV-SNP", "evidence_url": "https://1claw.xyz/shroud"}],
        voice={"tone": "technical"},
        do_say=["vault-aware"],
        do_not_say=["SOC 2 certified"],
        cta_library=[{"label": "Read docs", "url": "https://docs.1claw.xyz", "intent": "docs"}],
        keywords_seo=["AI agent security"],
        audiences=[{"persona": "Sec eng", "industries": ["AI"], "role_titles": ["Security Engineer"]}],
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind",
    ["hook", "cta", "hashtags", "brief_expand", "idea_seed", "reply_draft"],
)
def test_prompt_renders(plan, kind):
    # Map kind -> filename
    filename_map = {
        "hook": "hooks",
        "cta": "cta",
        "hashtags": "hashtags",
        "brief_expand": "brief_expand",
        "idea_seed": "idea_seed",
        "reply_draft": "reply_draft",
    }
    rendered, schema = render_prompt(
        filename_map[kind],
        gtm_plan=plan,
        brief="Test brief",
        platform="twitter" if kind == "hashtags" else None,
        extra={"original_text": "Test message", "count": 5},
    )
    assert "Shroud" in rendered or "vault-aware" in rendered or len(rendered) > 200


# -----------------------------------------------------------------------------
# Endpoint smoke tests
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestPhase4Endpoints:
    def test_hooks_queues(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(_url("generate_hooks", workspace), {"brief": "Announce X"})
        assert resp.status_code == 200
        assert AIGeneration.objects.filter(kind=GenerationKind.HOOK).exists()

    def test_cta_queues(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(_url("generate_cta", workspace), {"brief": "Draft post"})
        assert resp.status_code == 200
        assert AIGeneration.objects.filter(kind=GenerationKind.CTA).exists()

    def test_hashtags_queues(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(
                _url("generate_hashtags", workspace),
                {"brief": "AI agent security", "platform": "twitter"},
            )
        assert resp.status_code == 200
        assert AIGeneration.objects.filter(kind=GenerationKind.HASHTAGS).exists()

    def test_brief_expand_queues(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(
                _url("generate_brief_expand", workspace),
                {"brief": "MCP launch"},
            )
        assert resp.status_code == 200
        assert AIGeneration.objects.filter(kind=GenerationKind.BRIEF_EXPAND).exists()

    def test_idea_seed_with_count(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(
                _url("generate_idea_seed", workspace),
                {"brief": "", "count": "5"},
            )
        assert resp.status_code == 200
        gen = AIGeneration.objects.filter(kind=GenerationKind.IDEA_SEED).first()
        assert gen.input_payload["extra"]["count"] == 5

    def test_idea_seed_clamps_count(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(
                _url("generate_idea_seed", workspace),
                {"brief": "", "count": "999"},
            )
        assert resp.status_code == 200
        gen = AIGeneration.objects.filter(kind=GenerationKind.IDEA_SEED).first()
        assert gen.input_payload["extra"]["count"] == 20

    def test_reply_draft_queues(self, client_logged_in, workspace, owner_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            resp = client_logged_in.post(
                _url("generate_reply_draft", workspace),
                {"original_text": "Cool product!", "platform": "twitter"},
            )
        assert resp.status_code == 200
        gen = AIGeneration.objects.filter(kind=GenerationKind.REPLY_DRAFT).first()
        assert gen.input_payload["extra"]["original_text"] == "Cool product!"

    def test_reply_draft_requires_original_text(self, client_logged_in, workspace, owner_membership):
        resp = client_logged_in.post(_url("generate_reply_draft", workspace), {"original_text": ""})
        assert resp.status_code == 400

    def test_hooks_empty_brief_400(self, client_logged_in, workspace, owner_membership):
        resp = client_logged_in.post(_url("generate_hooks", workspace), {"brief": ""})
        assert resp.status_code == 400

    def test_viewer_denied_on_all(self, client_logged_in, workspace, viewer_membership):
        with patch("apps.ai.tasks.run_generation_task"):
            for endpoint, payload in [
                ("generate_hooks", {"brief": "x"}),
                ("generate_cta", {"brief": "x"}),
                ("generate_hashtags", {"brief": "x", "platform": "twitter"}),
                ("generate_brief_expand", {"brief": "x"}),
                ("generate_idea_seed", {"brief": ""}),
                ("generate_reply_draft", {"original_text": "x"}),
            ]:
                resp = client_logged_in.post(_url(endpoint, workspace), payload)
                assert resp.status_code == 403, f"{endpoint} should deny viewer"
