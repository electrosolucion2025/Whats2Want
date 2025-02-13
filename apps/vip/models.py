import uuid
from django.db import models
from apps.whatsapp.models import WhatsAppContact
from apps.tenants.models import Tenant

class VIPAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="Payment ID")
    contact = models.OneToOneField(WhatsAppContact, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    permissions = models.CharField(
        max_length=50,
        choices=[
            ("no_payment", "Sin pago"),
            ("priority", "Prioridad"),
            ("discount", "Descuento especial")
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("contact", "tenant")

    def __str__(self):
        return f"VIP {self.contact.phone_number} - {self.tenant.name}"
