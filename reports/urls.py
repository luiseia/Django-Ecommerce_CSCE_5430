from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("product/<slug:slug>/report/", views.report_merchant, name="report_merchant"),
]