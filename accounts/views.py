from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from .decorators import merchant_required
from .forms import EmailLoginForm, ProfileUpdateForm, UserRegistrationForm


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
