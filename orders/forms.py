from django import forms
from .models import ReturnRequest


class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Please explain why you want to return this order.",
                }
            )
        }