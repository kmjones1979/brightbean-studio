"""Tests for the GTMPlanRevision signal capture."""

from __future__ import annotations

import pytest

from apps.gtm.models import GTMPlanRevision


@pytest.mark.django_db
class TestRevisions:
    def test_revision_created_on_create(self, plan):
        revisions = GTMPlanRevision.objects.filter(plan=plan)
        assert revisions.count() == 1
        assert revisions.first().diff_summary == "Created plan"

    def test_revision_appended_on_content_change(self, plan):
        plan.value_props = ["A", "B"]
        plan.save()
        revisions = GTMPlanRevision.objects.filter(plan=plan).order_by("created_at")
        assert revisions.count() == 2
        latest = revisions.last()
        assert "value_props" in latest.diff_summary

    def test_no_revision_on_no_op_save(self, plan):
        plan.save()  # Same data
        # Pre-save hook stashes a snapshot equal to the current snapshot
        # Post-save hook should detect no change and skip
        assert GTMPlanRevision.objects.filter(plan=plan).count() == 1

    def test_revision_records_editor(self, plan, user):
        plan.value_props = ["new"]
        plan.last_edited_by = user
        plan.save()
        rev = GTMPlanRevision.objects.filter(plan=plan).order_by("-created_at").first()
        assert rev.edited_by == user

    def test_revision_snapshot_includes_content(self, plan):
        plan.value_props = ["X", "Y", "Z"]
        plan.save()
        rev = GTMPlanRevision.objects.filter(plan=plan).order_by("-created_at").first()
        assert rev.snapshot["value_props"] == ["X", "Y", "Z"]
