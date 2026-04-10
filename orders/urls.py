from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("orders/", views.order_history, name="order_history"),
    path("orders/<uuid:order_number>/", views.order_detail, name="order_detail"),
    path("orders/<uuid:order_number>/items/<int:item_id>/return/", views.request_return, name="request_return"),
    path("orders/<uuid:order_number>/return-requests/", views.return_request_list, name="return_request_list"),
]