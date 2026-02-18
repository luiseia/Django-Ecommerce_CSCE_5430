from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_history, name="order_history"),
    path("<uuid:order_number>/", views.order_detail, name="order_detail"),
]
