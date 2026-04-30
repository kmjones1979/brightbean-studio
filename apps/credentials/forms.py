"""Forms for configuring per-platform OAuth credentials."""

from __future__ import annotations

from django import forms

from apps.credentials.models import PlatformCredential

_INPUT = (
    "w-full px-3 py-2 rounded-lg border border-stone-200 focus:border-stone-400 focus:outline-none text-sm font-mono"
)


# Per-platform field schemas. Each entry is a list of (key, label, required, helptext) tuples.
PLATFORM_FIELDS: dict[str, list[tuple[str, str, bool, str]]] = {
    "facebook": [
        ("app_id", "App ID", True, "From your Meta app's Settings → Basic"),
        ("app_secret", "App Secret", True, ""),
    ],
    "instagram": [
        ("app_id", "App ID", True, "Same Meta app as Facebook"),
        ("app_secret", "App Secret", True, ""),
    ],
    "instagram_personal": [
        ("client_id", "Instagram App ID", True, "Different from the Facebook app — Instagram Login product"),
        ("client_secret", "Instagram App Secret", True, ""),
    ],
    "linkedin_personal": [
        ("client_id", "Client ID", True, "From linkedin.com/developers/apps → Auth tab"),
        ("client_secret", "Client Secret", True, ""),
    ],
    "linkedin_company": [
        ("client_id", "Client ID", True, "Same as LinkedIn Personal app"),
        ("client_secret", "Client Secret", True, ""),
    ],
    "tiktok": [
        ("client_key", "Client Key", True, "From developers.tiktok.com"),
        ("client_secret", "Client Secret", True, ""),
    ],
    "youtube": [
        ("client_id", "Google Client ID", True, "console.cloud.google.com OAuth 2.0 Client"),
        ("client_secret", "Google Client Secret", True, ""),
    ],
    "google_business": [
        ("client_id", "Google Client ID", True, "Same Google OAuth client as YouTube works"),
        ("client_secret", "Google Client Secret", True, ""),
    ],
    "pinterest": [
        ("app_id", "App ID", True, ""),
        ("app_secret", "App Secret", True, ""),
    ],
    "threads": [
        ("app_id", "App ID", True, "Meta app — same as Facebook"),
        ("app_secret", "App Secret", True, ""),
    ],
}


def make_credential_form(platform: str, *, instance: PlatformCredential | None = None):
    """Build a dynamic form for a specific platform."""
    fields = PLATFORM_FIELDS.get(platform, [])
    if not fields:
        return None

    form_fields = {}
    initial: dict = {}
    if instance and isinstance(instance.credentials, dict):
        for key, _label, _req, _help in fields:
            existing = instance.credentials.get(key, "")
            if existing:
                # Mask the existing value as a placeholder so the user knows it's set
                masked = "••••" + existing[-4:] if len(existing) > 4 else "••••"
                initial[key] = ""
                form_fields[key] = forms.CharField(
                    required=False,
                    widget=forms.TextInput(
                        attrs={
                            "class": _INPUT,
                            "placeholder": masked,
                            "autocomplete": "off",
                        }
                    ),
                    help_text=f"Currently set ({masked}). Leave blank to keep, or type to replace.",
                )
                continue
            form_fields[key] = forms.CharField(
                required=_req,
                widget=forms.TextInput(attrs={"class": _INPUT, "autocomplete": "off"}),
                help_text=_help,
            )
    else:
        for key, _label, _req, _help in fields:
            form_fields[key] = forms.CharField(
                required=_req,
                widget=forms.TextInput(attrs={"class": _INPUT, "autocomplete": "off"}),
                help_text=_help,
            )

    PlatformCredentialForm = type(  # noqa: N806 — dynamically-built form class
        f"PlatformCredentialForm_{platform}",
        (forms.BaseForm,),
        {"base_fields": form_fields},
    )
    return PlatformCredentialForm


def field_labels_for(platform: str) -> dict[str, str]:
    return {key: label for (key, label, _req, _help) in PLATFORM_FIELDS.get(platform, [])}
