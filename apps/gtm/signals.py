"""Signals for the GTM app — primarily revision capture."""

from __future__ import annotations

import json
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.gtm.models import GTMPlan, GTMPlanRevision

REVISION_FIELDS = [
    "name",
    "status",
    "audiences",
    "value_props",
    "proof_points",
    "voice",
    "do_say",
    "do_not_say",
    "competitors",
    "keywords_seo",
    "cta_library",
    "compliance_notes",
]


def _snapshot(plan: GTMPlan) -> dict[str, Any]:
    return {
        "id": str(plan.id),
        "partner_id": str(plan.partner_id),
        "product_id": str(plan.product_id) if plan.product_id else None,
        "problem_solution_id": (str(plan.problem_solution_id) if plan.problem_solution_id else None),
        **{f: getattr(plan, f) for f in REVISION_FIELDS},
    }


@receiver(pre_save, sender=GTMPlan)
def stash_previous_state(sender, instance: GTMPlan, **kwargs):
    """Stash the pre-save state on the instance so post_save can diff."""
    if instance.pk:
        try:
            prev = GTMPlan.objects.get(pk=instance.pk)
            instance._previous_snapshot = _snapshot(prev)
        except GTMPlan.DoesNotExist:
            instance._previous_snapshot = None
    else:
        instance._previous_snapshot = None


@receiver(post_save, sender=GTMPlan)
def capture_revision(sender, instance: GTMPlan, created: bool, **kwargs):
    current = _snapshot(instance)
    previous = getattr(instance, "_previous_snapshot", None)

    if created:
        diff_summary = "Created plan"
    elif previous == current:
        # No content change — skip revision (e.g., touch-only saves)
        return
    else:
        changed = [f for f in REVISION_FIELDS if previous and previous.get(f) != current.get(f)]
        diff_summary = "Changed: " + ", ".join(changed) if changed else "Updated plan"

    GTMPlanRevision.objects.create(
        plan=instance,
        snapshot=json.loads(json.dumps(current, cls=DjangoJSONEncoder)),
        diff_summary=diff_summary[:500],
        edited_by=instance.last_edited_by or instance.created_by,
    )
