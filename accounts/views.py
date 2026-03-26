import io
import json
import math
import random

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .decorators import merchant_required
from .forms import EmailLoginForm, ProfileUpdateForm, UserRegistrationForm
from .models import FaceCredential, User


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


class UserLogoutView(LogoutView):
    next_page = "products:home"


def _validate_descriptor(raw_descriptor):
    if not isinstance(raw_descriptor, list):
        raise ValueError("Descriptor must be a list.")
    if len(raw_descriptor) < 64 or len(raw_descriptor) > 512:
        raise ValueError("Descriptor length is invalid.")
    descriptor = [float(value) for value in raw_descriptor]
    return descriptor


def _euclidean_distance(first, second):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(first, second)))


def captcha_image(request):
    """Generate a captcha image for login and store text in session."""
    code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
    request.session["login_captcha"] = code

    width, height = 140, 48
    image = Image.new("RGB", (width, height), color=(248, 249, 250))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    for _ in range(6):
        draw.line(
            (
                random.randint(0, width),
                random.randint(0, height),
                random.randint(0, width),
                random.randint(0, height),
            ),
            fill=(150, 150, 150),
            width=1,
        )

    for index, char in enumerate(code):
        x = 15 + index * 22 + random.randint(-2, 2)
        y = 14 + random.randint(-4, 4)
        draw.text((x, y), char, font=font, fill=(40, 40, 40))

    for _ in range(120):
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=(random.randint(100, 220), random.randint(100, 220), random.randint(100, 220)),
        )

    image = image.filter(ImageFilter.SMOOTH)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@require_POST
def face_login(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        email = payload.get("email", "").strip()
        descriptor = _validate_descriptor(payload.get("descriptor"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "message": "Invalid face login payload."}, status=400)

    credentials = FaceCredential.objects.select_related("user").all()
    if email:
        credentials = credentials.filter(user__email__iexact=email)

    candidates = []
    for credential in credentials:
        stored = credential.descriptor or []
        if len(stored) != len(descriptor):
            continue
        distance = _euclidean_distance(stored, descriptor)
        candidates.append((distance, credential.user))

    if not candidates:
        if email:
            return JsonResponse(
                {"ok": False, "message": "No enrolled face found for this email. Please enroll first."},
                status=400,
            )
        return JsonResponse(
            {"ok": False, "message": "No enrolled faces found. Please enroll your face first."},
            status=400,
        )

    distance, user = min(candidates, key=lambda item: item[0])
    threshold = getattr(settings, "FACE_LOGIN_DISTANCE_THRESHOLD", 0.60)
    if distance > threshold:
        message = "Face not recognized. Try better lighting/angle, or re-enroll your face."
        if settings.DEBUG:
            message = f"{message} (distance={distance:.3f}, threshold={threshold:.3f})"
        return JsonResponse({"ok": False, "message": message}, status=401)

    login(request, user, backend="accounts.backends.EmailBackend")
    return JsonResponse({"ok": True, "redirect_url": reverse("products:home")})


@login_required
def face_enroll_page(request):
    has_enrolled = hasattr(request.user, "face_credential") and bool(request.user.face_credential.descriptor)
    return render(request, "accounts/face_enroll.html", {"has_enrolled": has_enrolled})


@login_required
@require_POST
def face_enroll(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        descriptor = _validate_descriptor(payload.get("descriptor"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "message": "Invalid face descriptor."}, status=400)

    credential, _ = FaceCredential.objects.get_or_create(user=request.user)
    credential.descriptor = descriptor
    credential.save(update_fields=["descriptor", "updated_at"])
    return JsonResponse({"ok": True, "message": "Face enrolled successfully."})


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
# Personal Page
# ---------------------------------------------------------------------------
@login_required
def personal_page(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your information has been updated.")
            return redirect("accounts:personal_page")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "accounts/personal_page.html", {"form": form})


# ---------------------------------------------------------------------------
# Role-specific dashboards
# ---------------------------------------------------------------------------
@login_required
@merchant_required
def merchant_dashboard(request):
    products = request.user.products.select_related("inventory").all()
    low_stock_count = sum(
        1 for p in products
        if hasattr(p, "inventory") and p.inventory.is_low_stock
    )
    return render(
        request,
        "accounts/merchant_dashboard.html",
        {"products": products, "low_stock_count": low_stock_count},
    )
