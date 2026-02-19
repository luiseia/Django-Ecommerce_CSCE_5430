from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("login/captcha.png", views.login_captcha_image, name="login_captcha_image"),
    path("password/forgot/", views.forgot_password, name="password_forgot"),
    path("password/verify/", views.verify_password_reset_code, name="password_reset_verify"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("merchant/dashboard/", views.merchant_dashboard, name="merchant_dashboard"),
]
