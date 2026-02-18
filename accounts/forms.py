from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
class UserRegistrationForm(UserCreationForm):
    """Sign-up form — asks for email, name, role, and password."""

    ROLE_CHOICES = [
        (User.Role.SHOPPER, "Shopper"),
        (User.Role.MERCHANT, "Merchant"),
    ]

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autofocus": True, "placeholder": "you@example.com"}),
    )
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial=User.Role.SHOPPER)
    store_name = forms.CharField(
        max_length=255,
        required=False,
        help_text="Required if registering as a Merchant.",
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "role",
            "store_name",
            "password1",
            "password2",
        ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == User.Role.MERCHANT and not cleaned.get("store_name"):
            self.add_error("store_name", "Merchants must provide a store name.")
        return cleaned


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class EmailLoginForm(AuthenticationForm):
    """Login form that labels the identifier field as *Email*."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "placeholder": "you@example.com"}),
    )


# ---------------------------------------------------------------------------
# Profile editing
# ---------------------------------------------------------------------------
class ProfileUpdateForm(forms.ModelForm):
    """Let users update their personal information."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
            "avatar",
            "store_name",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }
