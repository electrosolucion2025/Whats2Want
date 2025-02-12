import uuid
from django.db import models
from apps.whatsapp.models import WhatsAppContact
from apps.menu.models import Product

class Promotion(models.Model):
    """
    Modelo de Promoción flexible con códigos promocionales y fechas de validez.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)  # Código promocional único (ej. "PROMO10OFF")
    name = models.CharField(max_length=255)  # Ej. "10% de descuento en pedidos mayores a $10"
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=[
        ("percentage", "Porcentaje"),
        ("fixed", "Monto fijo"),
        ("free_product", "Producto gratis"),
    ])
    discount_value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # % o monto fijo
    applicable_products = models.ManyToManyField(Product, blank=True)  # Aplica a productos específicos
    min_order_amount = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # Monto mínimo
    max_uses_per_user = models.PositiveIntegerField(default=1)  # Límite por usuario
    start_date = models.DateTimeField(null=True, blank=True)  # Fecha de inicio de la promo
    end_date = models.DateTimeField(null=True, blank=True)  # Fecha de fin
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        """ Verifica si la promoción está activa y dentro del período de validez. """
        from django.utils.timezone import now
        return (
            self.is_active and
            (not self.start_date or self.start_date <= now()) and
            (not self.end_date or self.end_date >= now())
        )

    def __str__(self):
        return f"{self.code} - {self.name}"
    
class PromotionUsage(models.Model):
    """
    Registro de promociones utilizadas por usuarios.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(WhatsAppContact, on_delete=models.CASCADE, related_name="promotions_used")
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="usages")
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.promotion.code}"

