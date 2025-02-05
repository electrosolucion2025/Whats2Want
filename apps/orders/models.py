import uuid

from django.db import models
from apps.menu.models import Product, Extra
from apps.tenants.models import Tenant

# Modelo de Pedidos
class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)  # Relación con el inquilino
    phone_number = models.CharField(max_length=15)  # Número de teléfono del cliente
    order_number = models.CharField(max_length=20, unique=True)  # Número de pedido único
    notes = models.TextField(blank=True, null=True)  # Notas adicionales del cliente
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)  # Precio total del pedido
    payment_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pendiente'),
        ('PAID', 'Pagado'),
        ('FAILED', 'Fallido')
    ], default='PENDING')
    delivery_type = models.CharField(max_length=20, choices=[
        ('TAKEAWAY', 'Para llevar'),
        ('DINE_IN', 'En el local'),
        ('DELIVERY', 'A domicilio')
    ], default='TAKEAWAY')
    table_number = models.CharField(max_length=10, blank=True, null=True)  # Número de mesa (si aplica)
    printer_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pendiente'),
        ('PRINTED', 'Impreso'),
        ('FAILED', 'Fallido')
    ], default='PENDING')
    payment_reference = models.CharField(max_length=50, blank=True, null=True)  # Referencia del pago (Redsys)
    discount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)  # Descuento aplicado
    tax_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)  # Monto de impuestos
    is_scheduled = models.BooleanField(default=False)  # Indica si el pedido está programado
    scheduled_time = models.DateTimeField(blank=True, null=True)  # Hora programada para entrega o recogida

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('IN_PROGRESS', 'En preparación'),
        ('READY', 'Listo'),
        ('COMPLETED', 'Completado'),
        ('CANCELLED', 'Cancelado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"Pedido #{self.order_number} - {self.phone_number}"

# Modelo de Líneas de Pedido (Order Items)
class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)  # Relación con el inquilino
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=6, decimal_places=2)  # Precio unitario del producto
    final_price = models.DecimalField(max_digits=8, decimal_places=2)  # Precio final con extras y descuentos
    extras = models.ManyToManyField(Extra, blank=True)  # Extras asociados al producto
    exclusions = models.TextField(blank=True, null=True, help_text="Ingredientes a excluir, separados por comas")
    special_instructions = models.TextField(blank=True, null=True, help_text="Instrucciones especiales para este ítem")
    discount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)  # Descuento específico para el ítem
    tax_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)  # Impuestos aplicados al ítem
    preparation_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pendiente'),
        ('IN_PROGRESS', 'En preparación'),
        ('READY', 'Listo')
    ], default='PENDING')  # Estado de preparación del ítem
    custom_name = models.CharField(max_length=100, blank=True, null=True, help_text="Nombre personalizado del producto")
    served_at = models.DateTimeField(blank=True, null=True, help_text="Fecha y hora en que fue servido")

    def __str__(self):
        return f"{self.quantity}x {self.product.name} para Pedido #{self.order.order_number}"
