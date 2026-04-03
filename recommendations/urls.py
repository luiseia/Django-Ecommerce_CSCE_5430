from django.urls import path

from . import views

app_name = "recommendations"

urlpatterns = [
    path("home", views.api_home_recommendations, name="api_home"),
    path("product/<int:product_id>", views.api_product_recommendations, name="api_product"),
    path("cart", views.api_cart_recommendations, name="api_cart"),
]
