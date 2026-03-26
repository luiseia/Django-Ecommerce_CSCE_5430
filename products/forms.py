from django import forms

from .models import Inventory, Review


class InventoryUpdateForm(forms.ModelForm):
    """Form for merchants to update stock quantity."""

    restock_amount = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Amount to add"}),
        help_text="Enter a positive number to add to current stock.",
    )

    class Meta:
        model = Inventory
        fields = ["low_stock_threshold"]
        widgets = {
            "low_stock_threshold": forms.NumberInput(attrs={"class": "form-control"}),
        }


class ReviewForm(forms.ModelForm):
    """Form for submitting a product review."""

    RATING_CHOICES = [(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={
                "rows": 4,
                "class": "form-control",
                "placeholder": "Share your experience with this product…",
            }),
        }
