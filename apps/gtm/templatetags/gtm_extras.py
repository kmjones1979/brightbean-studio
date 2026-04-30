"""Template tags for the GTM app — dynamic attribute access and JSON pretty-printing."""

from __future__ import annotations

import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="attr")
def attr(obj, name):
    """Look up an attribute by name. Used to render dynamic GTM plan fields."""
    return getattr(obj, name, "")


@register.filter(name="safe_json")
def safe_json(value):
    """Pretty-print a JSON-serializable value for display."""
    if value in (None, "", [], {}):
        return mark_safe("<span class='text-stone-400'>—</span>")
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
