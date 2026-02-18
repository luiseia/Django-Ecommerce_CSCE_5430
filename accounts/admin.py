from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Administrator, Merchant, Shopper, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("email", "full_name", "role", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone_number", "date_of_birth", "avatar")}),
        ("Role & Store", {"fields": ("role", "store_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "role", "password1", "password2"),
            },
        ),
    )


# Register proxy models so they appear separately in admin
@admin.register(Shopper)
class ShopperAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.SHOPPER)


@admin.register(Merchant)
class MerchantAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.MERCHANT)


@admin.register(Administrator)
class AdministratorAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.ADMINISTRATOR)
