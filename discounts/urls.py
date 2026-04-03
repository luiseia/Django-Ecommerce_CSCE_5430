from django.urls import path
from . import views

app_name = 'discounts'

urlpatterns = [
    # Shopper discount application
    path('validate/', views.validate_discount, name='validate'),
    path('apply/<int:order_id>/', views.apply_discount, name='apply'),
    path('remove/<int:order_id>/', views.remove_discount, name='remove'),
    
    # Merchant discount management
    path('merchant/discounts/', views.merchant_discount_list, name='merchant_discount_list'),
    path('merchant/discounts/create/', views.merchant_discount_create, name='merchant_discount_create'),
    path('merchant/discounts/<int:discount_id>/edit/', views.merchant_discount_edit, name='merchant_discount_edit'),
    path('merchant/discounts/<int:discount_id>/delete/', views.merchant_discount_delete, name='merchant_discount_delete'),
    path('merchant/discounts/<int:discount_id>/', views.merchant_discount_detail, name='merchant_discount_detail'),
]
