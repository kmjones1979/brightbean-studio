"""Phase 5: cost sparkline endpoint + Generations tab on plan detail."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.ai.models import AIGeneration, AIWorkspaceConfig, GenerationKind, GenerationStatus


@pytest.fixture
def client_logged_in(db, user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
class TestSettingsPageSparkline:
    def test_includes_daily_spend_payload(self, client_logged_in, workspace, owner_membership):
        AIWorkspaceConfig.objects.create(workspace=workspace)
        AIGeneration.objects.create(
            workspace=workspace,
            kind=GenerationKind.CAPTION,
            provider="anthropic",
            model="claude-sonnet-4-6",
            status=GenerationStatus.SUCCEEDED,
            cost_usd_micro=12_500,
        )
        resp = client_logged_in.get(reverse("ai:settings", kwargs={"workspace_id": workspace.id}))
        assert resp.status_code == 200
        # The JSON payload is embedded in a <script id="spend-data">
        assert b"spend-data" in resp.content
        # Sparkline canvas present
        assert b"spend-sparkline" in resp.content

    def test_zero_spend_renders(self, client_logged_in, workspace, owner_membership):
        AIWorkspaceConfig.objects.create(workspace=workspace)
        resp = client_logged_in.get(reverse("ai:settings", kwargs={"workspace_id": workspace.id}))
        assert resp.status_code == 200


@pytest.mark.django_db
class TestDailySpendSeries:
    def test_aggregates_by_day(self, workspace):
        from apps.ai.views import _daily_spend_series

        AIGeneration.objects.create(
            workspace=workspace,
            kind=GenerationKind.CAPTION,
            provider="anthropic",
            model="x",
            status=GenerationStatus.SUCCEEDED,
            cost_usd_micro=5_000_000,
        )
        AIGeneration.objects.create(
            workspace=workspace,
            kind=GenerationKind.CAPTION,
            provider="anthropic",
            model="x",
            status=GenerationStatus.SUCCEEDED,
            cost_usd_micro=2_500_000,
        )
        from django.utils import timezone

        today = timezone.now().date()
        series = _daily_spend_series(workspace, today.replace(day=1))
        assert isinstance(series, list)
        assert all("day" in d and "cost_usd" in d for d in series)
        # Total spend across days should be 7.5
        total = sum(d["cost_usd"] for d in series)
        assert total == pytest.approx(7.5)
