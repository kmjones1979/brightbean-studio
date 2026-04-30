"""Prompt templates and rendering for AI generation kinds.

Templates live as plain .txt files in this directory and are rendered with
Django's Template engine. Every template starts with a header comment
specifying version, expected JSON schema, and changelog.
"""

from __future__ import annotations

from pathlib import Path

from django.template import Context, Template

from apps.ai.platform_specs import PLATFORM_SPECS

PROMPTS_DIR = Path(__file__).parent

# All prompts must end with this clause verbatim.
COMMON_TAIL = (
    "Return only valid JSON matching the schema. Never invent statistics, "
    "customer names, certifications, or capabilities not present in the GTM "
    "plan. If a requested claim cannot be supported by the proof_points or "
    "do_say arrays, omit it. Respect every entry in do_not_say. Stay within "
    "the platform's character limit minus 20 characters as a buffer."
)


def _read_template(name: str) -> str:
    """Read the raw template. Templates wrap their own bodies in
    `{% autoescape off %}` so apostrophes etc. stay literal — these prompts
    are fed to LLMs, not rendered as HTML.
    """
    path = PROMPTS_DIR / f"{name}.txt"
    text = path.read_text(encoding="utf-8")
    if "{% autoescape" not in text:
        text = "{% autoescape off %}" + text + "{% endautoescape %}"
    return text


def render_prompt(
    kind: str,
    *,
    gtm_plan,
    brief: str,
    platform: str | None = None,
    platforms: list[str] | None = None,
    extra: dict | None = None,
) -> tuple[str, dict | None]:
    """Render a prompt template for the given kind.

    Returns (rendered_system_prompt, json_schema_or_None).
    """
    template_text = _read_template(kind)
    template = Template(template_text)

    spec = PLATFORM_SPECS.get(platform) if platform else None
    specs_for_platforms = {p: PLATFORM_SPECS.get(p) for p in platforms if p in PLATFORM_SPECS} if platforms else {}

    ctx = Context(
        {
            "gtm_plan": gtm_plan,
            "platform": platform,
            "platform_spec": spec,
            "platforms": platforms or [],
            "platform_specs": specs_for_platforms,
            "brief": brief,
            "voice": getattr(gtm_plan, "voice", {}) if gtm_plan else {},
            "do_say": getattr(gtm_plan, "do_say", []) if gtm_plan else [],
            "do_not_say": getattr(gtm_plan, "do_not_say", []) if gtm_plan else [],
            "proof_points": getattr(gtm_plan, "proof_points", []) if gtm_plan else [],
            "cta_library": getattr(gtm_plan, "cta_library", []) if gtm_plan else [],
            "compliance_notes": (getattr(gtm_plan, "compliance_notes", "") if gtm_plan else ""),
            "common_tail": COMMON_TAIL,
            "extra": extra or {},
        }
    )

    rendered = template.render(ctx)
    schema = SCHEMAS.get(kind)
    return rendered, schema


# JSON schemas for structured output
SCHEMAS: dict[str, dict] = {
    "caption": {
        "type": "object",
        "additionalProperties": False,
        "required": ["variants"],
        "properties": {
            "variants": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["text", "char_count", "rationale"],
                    "properties": {
                        "text": {"type": "string"},
                        "char_count": {"type": "integer"},
                        "rationale": {"type": "string"},
                    },
                },
            }
        },
    },
    "multi_platform": {
        "type": "object",
        "additionalProperties": False,
        "required": ["variants"],
        "properties": {
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["platform", "text", "char_count", "hashtags"],
                    "properties": {
                        "platform": {"type": "string"},
                        "text": {"type": "string"},
                        "char_count": {"type": "integer"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "first_comment": {"type": "string"},
                    },
                },
            }
        },
    },
    "hook": {
        "type": "object",
        "required": ["hooks"],
        "properties": {
            "hooks": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["text", "style", "rationale"],
                    "properties": {
                        "text": {"type": "string"},
                        "style": {
                            "type": "string",
                            "enum": ["stat", "contrarian", "challenge", "observation", "comparison"],
                        },
                        "rationale": {"type": "string"},
                    },
                },
            }
        },
    },
    "cta": {
        "type": "object",
        "required": ["ctas"],
        "properties": {
            "ctas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["label", "url", "intent", "source"],
                    "properties": {
                        "label": {"type": "string"},
                        "url": {"type": "string"},
                        "intent": {
                            "type": "string",
                            "enum": ["signup", "demo", "docs", "download", "contact"],
                        },
                        "source": {"type": "string", "enum": ["library", "generated"]},
                    },
                },
            }
        },
    },
    "hashtags": {
        "type": "object",
        "required": ["broad", "niche", "branded"],
        "properties": {
            "broad": {"type": "array", "items": {"type": "string"}},
            "niche": {"type": "array", "items": {"type": "string"}},
            "branded": {"type": "array", "items": {"type": "string"}},
        },
    },
    "brief_expand": {
        "type": "object",
        "required": [
            "headline",
            "angle",
            "key_points",
            "cta_suggestion",
            "target_audience",
            "distribution",
        ],
        "properties": {
            "headline": {"type": "string"},
            "angle": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
            "cta_suggestion": {"type": "string"},
            "target_audience": {"type": "string"},
            "distribution": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["platform", "reason"],
                    "properties": {
                        "platform": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    },
    "idea_seed": {
        "type": "object",
        "required": ["ideas"],
        "properties": {
            "ideas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["title", "description", "target_audience", "suggested_platforms"],
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "target_audience": {"type": "string"},
                        "cta": {"type": "string"},
                        "suggested_platforms": {"type": "array", "items": {"type": "string"}},
                    },
                },
            }
        },
    },
    "reply_draft": {
        "type": "object",
        "required": ["replies"],
        "properties": {
            "replies": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "required": ["text", "style", "length"],
                    "properties": {
                        "text": {"type": "string"},
                        "style": {"type": "string", "enum": ["short", "with_cta"]},
                        "length": {"type": "integer"},
                    },
                },
            }
        },
    },
}


__all__ = [
    "render_prompt",
    "SCHEMAS",
    "COMMON_TAIL",
]
