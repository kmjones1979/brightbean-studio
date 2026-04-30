"""Credentials views — list per-platform credential cards and configure them."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.credentials.forms import PLATFORM_FIELDS, field_labels_for, make_credential_form
from apps.credentials.models import PlatformCredential


def _ensure_org(request):
    if not request.org or not request.org_membership:
        raise PermissionDenied("You are not in an organization.")
    if request.org_membership.org_role not in ("owner", "admin"):
        raise PermissionDenied("Only org owners/admins can manage credentials.")
    return request.org


@login_required
def credentials_list(request):
    org = _ensure_org(request)

    existing = {cred.platform: cred for cred in PlatformCredential.objects.for_org(org.id)}

    cards = []
    for platform, choice_label in PlatformCredential.Platform.choices:
        cred = existing.get(platform)
        cards.append(
            {
                "platform": platform,
                "label": choice_label,
                "is_configured": cred.is_configured if cred else False,
                "supported": platform in PLATFORM_FIELDS,
                "credential_id": cred.id if cred else None,
            }
        )

    return render(request, "credentials/list.html", {"cards": cards})


@login_required
@require_http_methods(["GET", "POST"])
def credentials_configure(request, platform: str):
    org = _ensure_org(request)

    if platform not in dict(PlatformCredential.Platform.choices):
        return redirect("credentials:list")

    cred = PlatformCredential.objects.filter(organization=org, platform=platform).first()

    FormCls = make_credential_form(platform, instance=cred)  # noqa: N806
    if FormCls is None:
        messages.info(
            request,
            f"{platform} uses session-based or per-instance auth — no app credentials needed.",
        )
        return redirect("credentials:list")

    if request.method == "POST":
        form = FormCls(request.POST)
        if form.is_valid():
            new_creds: dict = dict(cred.credentials) if cred and isinstance(cred.credentials, dict) else {}
            for key, _label, _req, _help in PLATFORM_FIELDS[platform]:
                value = form.cleaned_data.get(key, "").strip()
                if value:
                    new_creds[key] = value
            all_filled = all(bool(new_creds.get(k)) for (k, _l, req, _h) in PLATFORM_FIELDS[platform] if req)
            if cred:
                cred.credentials = new_creds
                cred.is_configured = all_filled
                cred.save()
            else:
                cred = PlatformCredential.objects.create(
                    organization=org,
                    platform=platform,
                    credentials=new_creds,
                    is_configured=all_filled,
                )
            messages.success(request, f"{platform} credentials saved.")
            return redirect("credentials:list")
    else:
        form = FormCls()

    return render(
        request,
        "credentials/configure.html",
        {
            "platform": platform,
            "platform_label": dict(PlatformCredential.Platform.choices)[platform],
            "form": form,
            "credential": cred,
            "field_labels": field_labels_for(platform),
        },
    )


@login_required
@require_POST
def credentials_delete(request, credential_id):
    org = _ensure_org(request)
    cred = get_object_or_404(PlatformCredential, id=credential_id, organization=org)
    cred.delete()
    messages.success(request, f"Removed credentials for {cred.platform}.")
    return redirect("credentials:list")
