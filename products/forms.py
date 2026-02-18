from django import forms

from .models import Review


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
