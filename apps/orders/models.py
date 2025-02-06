import uuid

from decimal import Decimal
from django.db import models

from apps.tenants.models import Tenant

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    order_number = models.CharField(max_length=20, unique=True)
    chat_session = models.ForeignKey('chat.ChatSession', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pendiente'),
        ('PAID', 'Pagado'),
        ('FAILED', 'Fallido')
    ], default='PENDING')
    delivery_type = models.CharField(max_length=20, choices=[
        ('DINE_IN', 'En el local'),
        ('TAKEAWAY', 'Para llevar'),
        ('DELIVERY', 'A domicilio')
    ], default='DINE_IN')
    table_number = models.CharField(max_length=10, blank=True, null=True)
    printer_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pendiente'),
        ('PRINTED', 'Impreso'),
        ('FAILED', 'Fallido')
    ], default='PENDING')
    payment_reference = models.CharField(max_length=50, blank=True, null=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    is_scheduled = models.BooleanField(default=False)
    scheduled_time = models.DateTimeField(blank=True, null=True)

    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('IN_PROGRESS', 'En preparación'),
        ('READY', 'Listo'),
        ('COMPLETED', 'Completado'),
        ('CANCELLED', 'Cancelado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pedido #{self.order_number} - {self.phone_number}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey("menu.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=6, decimal_places=2)  
    final_price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))  
    extras = models.JSONField(blank=True, null=True)  
    exclusions = models.JSONField(default=list, blank=True)
    special_instructions = models.TextField(blank=True, null=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    preparation_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pendiente'),
        ('IN_PROGRESS', 'En preparación'),
        ('READY', 'Listo')
    ], default='PENDING')
    custom_name = models.CharField(max_length=100, blank=True, null=True)
    served_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Convertir los precios de extras a Decimal
        extras_price = sum(Decimal(str(extra.get('price', '0.00'))) for extra in (self.extras or []))
        self.final_price = (self.price + extras_price - self.discount + self.tax_amount) * self.quantity
        super().save(*args, **kwargs)
        
    def formatted_description(self):
        """
        Devuelve una descripción formateada lista para imprimir, incluyendo extras, exclusiones e instrucciones especiales.
        """
        description = f"{self.quantity}x {self.product.name}"

        if self.extras:
            extras_list = ", ".join([f"{extra['name']} (+{extra['price']}€)" for extra in self.extras])
            description += f" (Extras: {extras_list})"

        if self.exclusions:
            exclusions_list = ", ".join(self.exclusions)
            description += f" (Sin: {exclusions_list})"

        if self.special_instructions:
            description += f" - {self.special_instructions}"

        return description

    def __str__(self):
        return f"{self.quantity}x {self.product.name} para Pedido #{self.order.order_number}"

