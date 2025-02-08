import uuid

from decimal import Decimal
from django.db import models

from apps.tenants.models import Tenant
from django.core.exceptions import ValidationError

PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('PAID', 'Paid'),
    ('FAILED', 'Failed')
]

DELIVERY_TYPE_CHOICES = [
    ('DINE_IN', 'Dine In'),
    ('TAKEAWAY', 'Takeaway'),
    ('DELIVERY', 'Delivery')
]

PRINTER_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('PRINTED', 'Printed'),
    ('FAILED', 'Failed')
]

STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('IN_PROGRESS', 'In Progress'),
    ('READY', 'Ready'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
]

class Order(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        verbose_name="Unique Order ID"
    )
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE,
        verbose_name="Associated Tenant"
    )
    phone_number = models.CharField(
        max_length=15, 
        verbose_name="Customer Phone Number"
    )  # ✅ Obligatorio
    order_number = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Order Number"
    )  # ✅ Obligatorio
    chat_session = models.ForeignKey(
        "chat.ChatSession", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Chat Session"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Additional Notes"
    )
    total_price = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Total Price (€)"
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='PENDING',
        verbose_name="Payment Status"
    )
    delivery_type = models.CharField(
        max_length=20, 
        choices=DELIVERY_TYPE_CHOICES, 
        default='DINE_IN',
        verbose_name="Delivery Type"
    )
    table_number = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        verbose_name="Table Number"
    )
    printer_status = models.CharField(
        max_length=20, 
        choices=PRINTER_STATUS_CHOICES, 
        default='PENDING',
        verbose_name="Printer Status"
    )
    payment_reference = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Payment Reference"
    )
    discount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Discount (€)"
    )
    tax_amount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Tax Amount (€)"
    )
    is_scheduled = models.BooleanField(
        default=False, 
        verbose_name="Is Scheduled?"
    )
    scheduled_time = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Scheduled Time"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING',
        verbose_name="Order Status"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Order Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Last Updated"
    )

    def __str__(self):
        return f"Order #{self.order_number} - {self.phone_number}"

    def get_total_items(self):
        """Devuelve la cantidad total de productos en el pedido."""
        return sum(item.quantity for item in self.items.all())

    def get_total_extras(self):
        """Calcula el precio total de los extras agregados a los productos."""
        return sum(item.get_extras_price() for item in self.items.all())

    def get_total_discount(self):
        """Devuelve el total de descuento aplicado al pedido."""
        return sum(item.discount for item in self.items.all())

    def get_final_total(self):
        """Calcula el total con impuestos y descuentos aplicados."""
        return self.total_price + self.tax_amount - self.discount

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="ID")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, verbose_name="Empresa (Tenant)")
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="Pedido")
    product = models.ForeignKey("menu.Product", on_delete=models.CASCADE, verbose_name="Producto")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Precio Unitario (€)")
    final_price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'), verbose_name="Precio Final (€)")
    extras = models.JSONField(blank=True, null=True, verbose_name="Extras")
    exclusions = models.JSONField(default=list, blank=True, verbose_name="Exclusiones")
    special_instructions = models.TextField(blank=True, null=True, verbose_name="Instrucciones Especiales")
    discount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), verbose_name="Descuento (%)")
    tax_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), verbose_name="IVA (%)")

    PREPARATION_STATUS_CHOICES = [
        ('PENDING', '🟡 Pendiente'),
        ('IN_PROGRESS', '🔵 En preparación'),
        ('READY', '🟢 Listo'),
    ]
    preparation_status = models.CharField(
        max_length=20, choices=PREPARATION_STATUS_CHOICES, default='PENDING', verbose_name="Estado de Preparación"
    )
    
    custom_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre Personalizado")
    served_at = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de Servicio")

    def save(self, *args, **kwargs):
        # Validar cantidad mínima
        if self.quantity < 1:
            raise ValidationError("La cantidad debe ser al menos 1.")

        # Convertir los precios de extras a Decimal
        extras_price = sum(Decimal(str(extra.get('price', '0.00'))) for extra in (self.extras or []))

        # Precio base del producto con extras y cantidad
        base_price = (self.price + extras_price) * self.quantity

        # Aplicar descuento como porcentaje
        discount_percentage = self.discount / Decimal(100)
        discount_amount = base_price * discount_percentage

        # Subtotal después del descuento
        subtotal = base_price - discount_amount

        # Aplicar IVA como porcentaje
        tax_percentage = self.tax_amount / Decimal(100)
        tax_amount = subtotal * tax_percentage

        # Precio final después de descuento e IVA
        self.final_price = subtotal + tax_amount
        self.tax_amount = tax_amount  # Guardamos el valor del impuesto calculado

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
