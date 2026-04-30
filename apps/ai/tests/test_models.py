"""Model-level tests for AIWorkspaceConfig + AIGeneration."""

from __future__ import annotations

from datetime import UTC, date

import pytest

from apps.ai.models import (
    AICredential,
    AICredentialKind,
    AIGeneration,
    AIWorkspaceConfig,
    GenerationKind,
    GenerationStatus,
)


@pytest.mark.django_db
class TestAIWorkspaceConfig:
    def test_defaults(self, workspace):
        config = AIWorkspaceConfig.objects.create(workspace=workspace)
        assert config.monthly_usd_cap == 25
        assert config.current_month_spend_micro == 0
        assert config.default_model == "claude-sonnet-4-6"
        assert config.routed_via_shroud is False
        assert config.use_oneclaw_vault is False

    def test_cap_remaining(self, workspace):
        config = AIWorkspaceConfig.objects.create(workspace=workspace, monthly_usd_cap=10)
        assert config.cap_remaining_micro == 10_000_000
        config.current_month_spend_micro = 7_500_000
        assert config.cap_remaining_micro == 2_500_000

    def test_is_over_cap(self, workspace):
        config = AIWorkspaceConfig.objects.create(workspace=workspace, monthly_usd_cap=5)
        assert not config.is_over_cap()
        config.current_month_spend_micro = 5_000_000
        assert config.is_over_cap()

    def test_add_spend(self, workspace):
        config = AIWorkspaceConfig.objects.create(workspace=workspace)
        config.add_spend(1_500_000)
        config.refresh_from_db()
        assert config.current_month_spend_micro == 1_500_000

    def test_roll_window_skipped_same_month(self, workspace):
        config = AIWorkspaceConfig.objects.create(
            workspace=workspace,
            current_month_spend_micro=2_000_000,
            spend_window_start=date(2026, 4, 1),
        )
        from datetime import datetime

        rolled = config.roll_window_if_new_month(datetime(2026, 4, 28, tzinfo=UTC))
        assert rolled is False
        assert config.current_month_spend_micro == 2_000_000

    def test_roll_window_resets_on_new_month(self, workspace):
        config = AIWorkspaceConfig.objects.create(
            workspace=workspace,
            current_month_spend_micro=2_000_000,
            spend_window_start=date(2026, 4, 1),
        )
        from datetime import datetime

        rolled = config.roll_window_if_new_month(datetime(2026, 5, 2, tzinfo=UTC))
        assert rolled is True
        assert config.current_month_spend_micro == 0
        assert config.spend_window_start.month == 5


@pytest.mark.django_db
class TestAIGeneration:
    def test_create(self, workspace):
        from decimal import Decimal

        gen = AIGeneration.objects.create(
            workspace=workspace,
            kind=GenerationKind.CAPTION,
            provider="anthropic",
            model="claude-sonnet-4-6",
            status=GenerationStatus.SUCCEEDED,
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd_micro=1_950,
        )
        assert gen.cost_usd == Decimal("0.001950")


@pytest.mark.django_db
class TestAICredential:
    def test_unique_per_org_kind(self, organization):
        AICredential.objects.create(
            organization=organization,
            kind=AICredentialKind.ANTHROPIC,
            credentials={"api_key": "x"},
            is_configured=True,
        )
        from django.db import IntegrityError, transaction

        with pytest.raises(IntegrityError), transaction.atomic():
            AICredential.objects.create(
                organization=organization,
                kind=AICredentialKind.ANTHROPIC,
                credentials={"api_key": "y"},
            )

    def test_encryption_round_trip(self, organization):
        cred = AICredential.objects.create(
            organization=organization,
            kind=AICredentialKind.OPENAI,
            credentials={"api_key": "sk-secret"},
        )
        from_db = AICredential.objects.get(pk=cred.pk)
        assert from_db.credentials == {"api_key": "sk-secret"}
