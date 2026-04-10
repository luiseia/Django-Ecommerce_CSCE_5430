from django import forms
from .models import ReturnRequest


class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ["quantity", "reason"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Please explain why you want to return this item.",
                }
            ),
        }

    def __init__(self, *args, order_item=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_item = order_item
        if order_item:
            self.fields["quantity"].widget.attrs["max"] = order_item.quantity

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        if self.order_item and quantity > self.order_item.quantity:
            raise forms.ValidationError("You cannot return more than you purchased.")
        return quantity