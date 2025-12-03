"""UI forms for audit trail views."""

from __future__ import annotations

from django import forms


class HistorySearchForm(forms.Form):
    """Validate parameters for history lookup requests."""

    model = forms.CharField(
        required=False,
        label="Model label",
        help_text="Django label like app.Model",
        widget=forms.TextInput(
            attrs={"class": "input-control w-full", "placeholder": "app.Model"}
        ),
    )
    object_id = forms.CharField(
        required=False,
        label="Object ID",
        widget=forms.TextInput(
            attrs={"class": "input-control w-full", "placeholder": "Primary key"}
        ),
    )
    user_id = forms.CharField(
        required=False,
        label="User ID",
        widget=forms.TextInput(
            attrs={"class": "input-control w-full", "placeholder": "Actor ID"}
        ),
    )
    limit = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        initial=25,
        label="Results per page",
        widget=forms.NumberInput(attrs={"class": "input-control w-full"}),
    )
    cursor = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean(self):  # noqa: ANN101
        cleaned = super().clean()
        object_id = cleaned.get("object_id")
        user_id = cleaned.get("user_id")
        if not object_id and not user_id:
            raise forms.ValidationError("Provide an object ID, user ID, or both.")
        if object_id and not cleaned.get("model"):
            raise forms.ValidationError(
                "Model label is required when querying by object."
            )
        return cleaned

    def get_limit(self) -> int:
        value = self.cleaned_data.get("limit")
        if value is None:
            return 25
        return int(value)
