"""Tests for prompt rendering — every kind renders against a fixture plan,
and the JSON schema is non-empty.
"""

from __future__ import annotations

import pytest

from apps.ai.prompts import COMMON_TAIL, SCHEMAS, render_prompt


@pytest.fixture
def plan_with_content(db, workspace):
    from apps.gtm.models import GTMPlan, Partner, Product

    partner = Partner.objects.create(workspace=workspace, name="1Claw")
    product = Product.objects.create(partner=partner, name="Shroud", tagline="TEE LLM proxy")
    return GTMPlan.objects.create(
        workspace=workspace,
        partner=partner,
        product=product,
        name="Shroud — Sec Eng",
        value_props=["Vault-aware redaction", "Inside the TEE"],
        proof_points=[{"claim": "AMD SEV-SNP", "evidence_url": "https://1claw.xyz/shroud"}],
        voice={"tone": "technical", "we_vs_i": "we"},
        do_say=["vault-aware", "Aho-Corasick exact match"],
        do_not_say=["SOC 2 certified"],
        cta_library=[{"label": "Read docs", "url": "https://docs.1claw.xyz/docs/guides/shroud", "intent": "docs"}],
        compliance_notes="No SOC 2 claims.",
    )


@pytest.mark.django_db
class TestCaptionPrompt:
    def test_renders_with_plan(self, plan_with_content):
        rendered, schema = render_prompt(
            "caption",
            gtm_plan=plan_with_content,
            brief="Announce MCP server update",
            platform="twitter",
        )
        assert "Shroud" in rendered
        assert "vault-aware" in rendered
        assert "SOC 2 certified" in rendered  # listed as banned
        assert "AMD SEV-SNP" in rendered
        assert COMMON_TAIL in rendered
        assert schema is not None
        assert schema["properties"]["variants"]["minItems"] == 3

    def test_renders_without_plan(self, db):
        rendered, schema = render_prompt(
            "caption",
            gtm_plan=None,
            brief="Test brief",
            platform="bluesky",
        )
        assert "Test brief" in rendered
        assert COMMON_TAIL in rendered
        assert schema is not None

    def test_unknown_platform_still_renders(self, plan_with_content):
        # Falls back to the brief + tail without a platform_spec
        rendered, _ = render_prompt(
            "caption",
            gtm_plan=plan_with_content,
            brief="x",
            platform="unknown_platform",
        )
        assert "x" in rendered


@pytest.mark.django_db
class TestMultiPlatformPrompt:
    def test_renders_for_multiple_platforms(self, plan_with_content):
        rendered, schema = render_prompt(
            "multi_platform",
            gtm_plan=plan_with_content,
            brief="Big announcement",
            platforms=["twitter", "linkedin_personal", "bluesky"],
        )
        assert "twitter" in rendered
        assert "linkedin_personal" in rendered
        assert "bluesky" in rendered
        assert COMMON_TAIL in rendered
        assert schema is not None


def test_schema_keys_match_known_kinds():
    expected_kinds = {"caption", "multi_platform"}
    assert expected_kinds.issubset(set(SCHEMAS.keys()))
