import uuid
from django.db import models
from apps.tenants.models import Tenant
from apps.orders.models import Order
from apps.whatsapp.models import WhatsAppContact


class Promotion(models.Model):
    PROMO_TYPE_CHOICES = [
        ("percentage", "Percentage Discount"),
        ("fixed_amount", "Fixed Amount Discount"),
        ("free_product", "Free Product"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="ID")
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="promotions", verbose_name="Tenant"
    )
    code = models.CharField(
        max_length=50, unique=True, help_text="Promo code (e.g., 'PROMOCAFE')", verbose_name="Promo Code"
    )
    description = models.TextField(help_text="Promotion description", verbose_name="Description")
    promo_type = models.CharField(
        max_length=20, choices=PROMO_TYPE_CHOICES, verbose_name="Promotion Type"
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="If it's a discount (percentage or fixed), this is the value",
        verbose_name="Discount Value"
    )
    free_product = models.ForeignKey(
        "menu.Product", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="If the promo gives a free product, specify which one",
        verbose_name="Free Product"
    )
    min_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Minimum order value required to apply the promotion",
        verbose_name="Minimum Order Value"
    )
    start_date = models.DateTimeField(help_text="Promotion start date", verbose_name="Start Date")
    end_date = models.DateTimeField(help_text="Promotion end date", verbose_name="End Date")
    is_active = models.BooleanField(default=True, help_text="Whether the promotion is active", verbose_name="Is Active")
    max_redemptions_per_user = models.IntegerField(
        null=True, blank=True,
        help_text="Limit of uses per user (e.g., 1 for 'first purchase only')",
        verbose_name="Max Redemptions Per User"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"

    def __str__(self):
        return f"{self.code} - {self.description}"


class PromotionRedemption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="ID")
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="redemptions", verbose_name="Promotion"
    )
    user = models.ForeignKey(
        WhatsAppContact, on_delete=models.CASCADE, related_name="used_promotions", verbose_name="User"
    )
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="applied_promotion", verbose_name="Order"
    )
    redeemed_at = models.DateTimeField(auto_now_add=True, verbose_name="Redeemed At")

    class Meta:
        unique_together = ("promotion", "user")
        verbose_name = "Promotion Redemption"
        verbose_name_plural = "Promotion Redemptions"

    def __str__(self):
        return f"{self.user.phone_number} used {self.promotion.code} on order {self.order.id}"
