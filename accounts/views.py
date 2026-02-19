import secrets
import time

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .decorators import merchant_required
from .forms import (
    EmailLoginForm,
    PasswordResetOTPForm,
    PasswordResetRequestForm,
    ProfileUpdateForm,
    UserRegistrationForm,
)

User = get_user_model()

OTP_SESSION_KEY = "password_reset_otp_map"
OTP_EXPIRE_SECONDS = 10 * 60


def _generate_login_captcha(request):
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = "".join(secrets.choice(chars) for _ in range(5))
    request.session["login_captcha_code"] = code
    request.session.modified = True
    return code


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="accounts.backends.EmailBackend")
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("products:home")
    else:
        form = UserRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


# ---------------------------------------------------------------------------
# Login / Logout (class-based, using our custom form)
# ---------------------------------------------------------------------------
class EmailLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        _generate_login_captcha(request)
        return super().get(request, *args, **kwargs)

    def form_invalid(self, form):
        _generate_login_captcha(self.request)
        return super().form_invalid(form)


class UserLogoutView(LogoutView):
    next_page = "products:home"


def login_captcha_image(request):
    code = request.session.get("login_captcha_code")
    if request.GET.get("refresh") == "1" or not code:
        code = _generate_login_captcha(request)

    width, height = 170, 50
    image = Image.new("RGB", (width, height), (248, 249, 250))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    for _ in range(5):
        x1 = secrets.randbelow(width)
        y1 = secrets.randbelow(height)
        x2 = secrets.randbelow(width)
        y2 = secrets.randbelow(height)
        draw.line((x1, y1, x2, y2), fill=(160, 160, 160), width=1)

    for i, ch in enumerate(code):
        x = 16 + i * 28 + secrets.randbelow(4)
        y = 15 + secrets.randbelow(8)
        color = (40 + secrets.randbelow(90), 40 + secrets.randbelow(90), 40 + secrets.randbelow(90))
        draw.text((x, y), ch, font=font, fill=color)

    image = image.filter(ImageFilter.SMOOTH)
    response = HttpResponse(content_type="image/png")
    image.save(response, "PNG")
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


def forgot_password(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                code = "".join(secrets.choice("0123456789") for _ in range(6))
                otp_map = request.session.get(OTP_SESSION_KEY, {})
                otp_map[email] = {"code": code, "ts": int(time.time())}
                request.session[OTP_SESSION_KEY] = otp_map
                request.session.modified = True
                try:
                    send_mail(
                        subject="ShopProject password reset verification code",
                        message=(
                            f"Your verification code is: {code}\n\n"
                            f"This code expires in {OTP_EXPIRE_SECONDS // 60} minutes."
                        ),
                        from_email=None,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception:
                    form.add_error(None, "Email sending failed. Please verify SMTP settings.")
                    return render(request, "accounts/forgot_password.html", {"form": form})

            messages.success(
                request,
                "If the email exists, a 6-digit verification code has been sent.",
            )
            return redirect("accounts:password_reset_verify")
    else:
        form = PasswordResetRequestForm()
    return render(request, "accounts/forgot_password.html", {"form": form})


def verify_password_reset_code(request):
    if request.method == "POST":
        form = PasswordResetOTPForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            code = form.cleaned_data["code"]
            otp_map = request.session.get(OTP_SESSION_KEY, {})
            otp_data = otp_map.get(email)
            if not otp_data:
                form.add_error("code", "No verification request found for this email.")
            elif int(time.time()) - int(otp_data.get("ts", 0)) > OTP_EXPIRE_SECONDS:
                form.add_error("code", "Verification code has expired. Please request a new one.")
            elif otp_data.get("code") != code:
                form.add_error("code", "Invalid verification code.")
            else:
                user = User.objects.filter(email__iexact=email, is_active=True).first()
                if not user:
                    form.add_error("email", "No active account found for this email.")
                else:
                    user.set_password(form.cleaned_data["new_password1"])
                    user.save(update_fields=["password"])
                    otp_map.pop(email, None)
                    request.session[OTP_SESSION_KEY] = otp_map
                    request.session.modified = True
                    messages.success(request, "Password has been reset. Please log in.")
                    return redirect("accounts:login")
    else:
        initial_email = request.GET.get("email", "").strip()
        form = PasswordResetOTPForm(initial={"email": initial_email})

    return render(request, "accounts/password_reset_verify.html", {"form": form})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    order_history = request.user.get_order_history()

    return render(
        request,
        "accounts/profile.html",
        {"form": form, "order_history": order_history},
    )


# ---------------------------------------------------------------------------
# Role-specific dashboards
# ---------------------------------------------------------------------------
@login_required
@merchant_required
def merchant_dashboard(request):
    products = request.user.products.all()
    return render(
        request,
        "accounts/merchant_dashboard.html",
        {"products": products},
    )
