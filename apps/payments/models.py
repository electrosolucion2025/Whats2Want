import uuid

from django.db import models
from apps.tenants.models import Tenant
from apps.orders.models import Order

# Modelo de Pagos
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')  # Relación con el pedido
    payment_id = models.CharField(max_length=100, unique=True)  # ID de pago generado por Redsys
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Monto total del pago
    currency = models.CharField(max_length=10, default='EUR')  # Moneda
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ], default='pending')  # Estado del pago
    payment_method = models.CharField(max_length=50, blank=True, null=True)  # Método de pago usado
    transaction_date = models.DateTimeField(auto_now_add=True)  # Fecha y hora de la transacción
    authorization_code = models.CharField(max_length=50, blank=True, null=True)  # Código de autorización de Redsys
    response_code = models.CharField(max_length=10, blank=True, null=True)  # Código de respuesta de Redsys
    card_last_digits = models.CharField(max_length=4, blank=True, null=True)  # Últimos 4 dígitos de la tarjeta
    refund_reason = models.TextField(blank=True, null=True)  # Motivo del reembolso (si aplica)
    created_at = models.DateTimeField(auto_now_add=True)  # Fecha de creación
    updated_at = models.DateTimeField(auto_now=True)  # Fecha de última actualización

    def __str__(self):
        return f'Payment {self.payment_id} - {self.status}'
