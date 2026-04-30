"""Tests for the run_generation service: cost accounting + cap enforcement."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.ai.models import (
    AIGeneration,
    AIWorkspaceConfig,
    GenerationKind,
    GenerationStatus,
)
from apps.ai.providers.stub import StubProvider
from apps.ai.providers.types import ProviderError
from apps.ai.services import CapExceededError, run_generation


def _patch_build_provider(stub):
    """Patch the factory so run_generation uses our stub."""
    return patch("apps.ai.services.build_provider", return_value=stub)


@pytest.mark.django_db
class TestRunGeneration:
    def test_succeeded_path_records_usage_and_cost(self, workspace, user):
        stub = StubProvider(prompt_tokens=1000, completion_tokens=1000)
        with _patch_build_provider(stub):
            gen = run_generation(
                workspace=workspace,
                actor=user,
                kind=GenerationKind.CAPTION,
                messages=[{"role": "user", "content": "hi"}],
                input_payload={"brief": "test"},
                model="claude-sonnet-4-6",
            )

        assert gen.status == GenerationStatus.SUCCEEDED
        assert gen.prompt_tokens == 1000
        assert gen.completion_tokens == 1000
        # Sonnet 4.6: $3/M input + $15/M output -> 3000 + 15000 = 18000 micro
        assert gen.cost_usd_micro == 18_000
        assert gen.completed_at is not None

    def test_spend_added_to_workspace_config(self, workspace, user):
        stub = StubProvider(prompt_tokens=1000, completion_tokens=1000)
        with _patch_build_provider(stub):
            run_generation(
                workspace=workspace,
                actor=user,
                kind=GenerationKind.CAPTION,
                messages=[{"role": "user", "content": "hi"}],
                input_payload={},
                model="claude-sonnet-4-6",
            )
        config = AIWorkspaceConfig.objects.get(workspace=workspace)
        assert config.current_month_spend_micro == 18_000

    def test_blocked_status_when_shroud_blocks(self, workspace, user):
        stub = StubProvider(raise_block=True)
        with _patch_build_provider(stub):
            gen = run_generation(
                workspace=workspace,
                actor=user,
                kind=GenerationKind.CAPTION,
                messages=[{"role": "user", "content": "hi"}],
                input_payload={},
                model="x",
            )
        assert gen.status == GenerationStatus.BLOCKED_BY_SHROUD
        assert "Blocked" in gen.error_message

    def test_failed_status_on_provider_error(self, workspace, user):
        stub = StubProvider(raise_error=ProviderError("upstream broken"))
        with _patch_build_provider(stub):
            gen = run_generation(
                workspace=workspace,
                actor=user,
                kind=GenerationKind.CAPTION,
                messages=[{"role": "user", "content": "hi"}],
                input_payload={},
                model="x",
            )
        assert gen.status == GenerationStatus.FAILED
        assert "upstream broken" in gen.error_message

    def test_cap_blocks_new_generations(self, workspace, user):
        AIWorkspaceConfig.objects.create(
            workspace=workspace,
            monthly_usd_cap=1,
            current_month_spend_micro=1_000_000,
        )
        with pytest.raises(CapExceededError):
            run_generation(
                workspace=workspace,
                actor=user,
                kind=GenerationKind.CAPTION,
                messages=[{"role": "user", "content": "hi"}],
                input_payload={},
            )
        # No row written
        assert AIGeneration.objects.for_workspace(workspace.id).count() == 0

    def test_unknown_kind_raises(self, workspace, user):
        with pytest.raises(ValueError, match="Unknown kind"):
            run_generation(
                workspace=workspace,
                actor=user,
                kind="not-real",
                messages=[],
                input_payload={},
            )
