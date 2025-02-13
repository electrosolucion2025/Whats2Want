from django.contrib import admin
from apps.promotions.models import Promotion, PromotionRedemption


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "code", "description", "promo_type", "discount_value", "free_product",
        "start_date", "end_date", "is_active", "max_redemptions_per_user"
    )
    list_filter = ("promo_type", "is_active", "start_date", "end_date", "tenant")
    search_fields = ("code", "description", "tenant__name")
    ordering = ("-start_date",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("tenant", "free_product")

    fieldsets = (
        ("General Info", {
            "fields": ("tenant", "code", "description", "promo_type", "is_active")
        }),
        ("Discount Settings", {
            "fields": ("discount_value", "free_product", "min_order_value"),
            "classes": ("collapse",)  # Ocultar por defecto
        }),
        ("Validity", {
            "fields": ("start_date", "end_date", "max_redemptions_per_user")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    list_editable = ("is_active",)  # Permite activar/desactivar sin entrar en detalles


@admin.register(PromotionRedemption)
class PromotionRedemptionAdmin(admin.ModelAdmin):
    list_display = ("promotion", "user", "order", "redeemed_at")
    list_filter = ("promotion", "redeemed_at")
    search_fields = ("promotion__code", "user__phone_number", "order__id")
    ordering = ("-redeemed_at",)
    autocomplete_fields = ("promotion", "user", "order")
