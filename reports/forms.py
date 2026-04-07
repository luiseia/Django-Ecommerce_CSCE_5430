from django import forms
from .models import MerchantReport


class MerchantReportForm(forms.ModelForm):
    class Meta:
        model = MerchantReport
        fields = ["reason", "description"]
        widgets = {
            "reason": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Please describe the issue.",
                }
            ),
        }