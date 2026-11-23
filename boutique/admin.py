"""Admin registrations for the catalogue and customer accounts."""

from django.contrib import admin

from .models import CartItem, CodeSequence, CustomerAccount, Dress


@admin.register(Dress)
class DressAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "size", "price", "quantity", "is_active")
    list_filter = ("category", "size", "is_active")
    search_fields = ("code", "name", "color", "fabric")
    readonly_fields = ("code", "created_at", "updated_at")


@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = ("username", "phone", "address", "created_at", "last_login")
    search_fields = ("username", "phone")
    readonly_fields = ("created_at", "updated_at", "last_login")
    exclude = ("password",)

    def has_add_permission(self, request) -> bool:
        # Accounts are created from the storefront signup form.
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("customer", "dress", "quantity", "created_at")
    search_fields = ("customer__username", "dress__name", "dress__code")
    readonly_fields = ("created_at",)


@admin.register(CodeSequence)
class CodeSequenceAdmin(admin.ModelAdmin):
    list_display = ("prefix", "last_value")
    readonly_fields = ("prefix", "last_value")
