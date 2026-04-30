"""Forms for the GTM app.

Each form maps to a tab on the plan detail page so HTMX can swap
just the affected card on save.
"""

from __future__ import annotations

from django import forms

from apps.gtm.models import GTMPlan, Partner, ProblemSolution, Product

_INPUT = "w-full px-3 py-2 rounded-lg border border-stone-200 focus:border-stone-400 focus:outline-none text-sm"
_TEXTAREA = _INPUT + " min-h-[120px]"


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ("name", "website", "notes")
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "required": True}),
            "website": forms.URLInput(attrs={"class": _INPUT}),
            "notes": forms.Textarea(attrs={"class": _TEXTAREA}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "partner",
            "name",
            "tagline",
            "category",
            "homepage_url",
            "docs_url",
            "pricing_url",
        )
        widgets = {
            "partner": forms.Select(attrs={"class": _INPUT}),
            "name": forms.TextInput(attrs={"class": _INPUT, "required": True}),
            "tagline": forms.TextInput(attrs={"class": _INPUT}),
            "category": forms.TextInput(attrs={"class": _INPUT}),
            "homepage_url": forms.URLInput(attrs={"class": _INPUT}),
            "docs_url": forms.URLInput(attrs={"class": _INPUT}),
            "pricing_url": forms.URLInput(attrs={"class": _INPUT}),
        }


class ProblemSolutionForm(forms.ModelForm):
    class Meta:
        model = ProblemSolution
        fields = (
            "product",
            "problem_statement",
            "solution_statement",
            "target_persona",
            "pain_intensity",
            "is_primary",
        )
        widgets = {
            "product": forms.Select(attrs={"class": _INPUT}),
            "problem_statement": forms.Textarea(attrs={"class": _TEXTAREA}),
            "solution_statement": forms.Textarea(attrs={"class": _TEXTAREA}),
            "target_persona": forms.TextInput(attrs={"class": _INPUT}),
            "pain_intensity": forms.Select(attrs={"class": _INPUT}),
        }


class GTMPlanForm(forms.ModelForm):
    """Top-of-page form: name, status, partner/product/problem-solution links."""

    class Meta:
        model = GTMPlan
        fields = ("name", "status", "partner", "product", "problem_solution")
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "required": True}),
            "status": forms.Select(attrs={"class": _INPUT}),
            "partner": forms.Select(attrs={"class": _INPUT}),
            "product": forms.Select(attrs={"class": _INPUT}),
            "problem_solution": forms.Select(attrs={"class": _INPUT}),
        }


class GTMPlanComplianceForm(forms.ModelForm):
    class Meta:
        model = GTMPlan
        fields = ("compliance_notes",)
        widgets = {
            "compliance_notes": forms.Textarea(attrs={"class": _TEXTAREA}),
        }


# JSONField helper forms -- each tab edits one JSON column.
# Keeping these simple Textarea+JSON parsing for v1; richer editors come later.


class _JSONFieldForm(forms.Form):
    raw_json = forms.CharField(
        widget=forms.Textarea(attrs={"class": _TEXTAREA + " font-mono text-xs"}),
        required=False,
    )

    def __init__(self, *args, initial_data=None, **kwargs):
        import json

        super().__init__(*args, **kwargs)
        if initial_data is not None and "raw_json" not in self.data:
            self.fields["raw_json"].initial = json.dumps(initial_data, indent=2)

    def clean_raw_json(self):
        import json

        raw = self.cleaned_data.get("raw_json", "").strip()
        if not raw:
            return self.empty_value()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}") from e

    def empty_value(self):
        return []


class AudiencesForm(_JSONFieldForm):
    pass


class ValuePropsForm(_JSONFieldForm):
    pass


class ProofPointsForm(_JSONFieldForm):
    pass


class DoSayForm(_JSONFieldForm):
    pass


class DoNotSayForm(_JSONFieldForm):
    pass


class CompetitorsForm(_JSONFieldForm):
    pass


class KeywordsForm(_JSONFieldForm):
    pass


class CTALibraryForm(_JSONFieldForm):
    pass


class VoiceForm(_JSONFieldForm):
    def empty_value(self):
        return {}
