from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password

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
    captcha = forms.CharField(
        label="Captcha",
        max_length=8,
        help_text="Enter the characters shown in the image.",
    )

    def clean_captcha(self):
        value = self.cleaned_data["captcha"].strip().upper()
        session_code = (self.request.session.get("login_captcha_code") or "").upper()
        if not session_code or value != session_code:
            raise forms.ValidationError("Invalid captcha.")
        return value


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


# ---------------------------------------------------------------------------
# Password reset with email OTP
# ---------------------------------------------------------------------------
class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autofocus": True, "placeholder": "you@example.com"}),
    )


class PasswordResetOTPForm(forms.Form):
    email = forms.EmailField()
    code = forms.CharField(
        max_length=6,
        min_length=6,
        help_text="Enter the 6-digit verification code sent to your email.",
    )
    new_password1 = forms.CharField(widget=forms.PasswordInput, label="New password")
    new_password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm new password")

    def clean_code(self):
        code = self.cleaned_data["code"]
        if not code.isdigit():
            raise forms.ValidationError("Verification code must be 6 digits.")
        return code

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        password2 = cleaned.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "The two passwords do not match.")
        if password1:
            validate_password(password1)
        return cleaned
