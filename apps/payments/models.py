import uuid

from django.db import models

from apps.tenants.models import Tenant
from apps.orders.models import Order

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="Payment ID")
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, verbose_name="Tenant"
    )
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment", verbose_name="Order"
    )
    payment_id = models.CharField(max_length=100, unique=True, verbose_name="Redsys Payment ID")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount (€)")
    currency = models.CharField(max_length=10, default="EUR", verbose_name="Currency")
    status = models.CharField(
        max_length=50,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="pending",
        verbose_name="Payment Status",
    )
    payment_method = models.CharField(max_length=50, blank=True, null=True, verbose_name="Payment Method")
    transaction_date = models.DateTimeField(auto_now_add=True, verbose_name="Transaction Date")
    authorization_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Authorization Code")
    response_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Response Code")
    card_last_digits = models.CharField(max_length=4, blank=True, null=True, verbose_name="Card Last 4 Digits")
    refund_reason = models.TextField(blank=True, null=True, verbose_name="Refund Reason")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment {self.payment_id} - {self.get_status_display()}"
