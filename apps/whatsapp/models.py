import uuid
from django.db import models
from apps.tenants.models import Tenant

# 📌 **Modelo de Mensajes de WhatsApp**
class WhatsAppMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, verbose_name="Tenant")
    message_id = models.CharField(max_length=100, unique=True, verbose_name="ID del Mensaje")
    from_number = models.CharField(max_length=20, verbose_name="Número Remitente")
    to_number = models.CharField(max_length=20, verbose_name="Número Destinatario")
    message_type = models.CharField(
        max_length=50,
        choices=[
            ("text", "Texto"),
            ("image", "Imagen"),
            ("audio", "Audio"),
            ("video", "Video"),
            ("document", "Documento"),
            ("sticker", "Sticker"),
            ("location", "Ubicación"),
        ],
        verbose_name="Tipo de Mensaje",
    )
    content = models.TextField(blank=True, null=True, verbose_name="Contenido")
    status = models.CharField(
        max_length=50,
        choices=[
            ("sent", "Enviado"),
            ("delivered", "Entregado"),
            ("read", "Leído"),
            ("failed", "Fallido"),
        ],
        default="sent",
        verbose_name="Estado",
    )
    direction = models.CharField(
        max_length=10,
        choices=[("inbound", "Entrante"), ("outbound", "Saliente")],
        verbose_name="Dirección",
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")

    class Meta:
        verbose_name = "Mensaje de WhatsApp"
        verbose_name_plural = "Mensajes de WhatsApp"

    def __str__(self):
        return f"Mensaje {self.message_id} - {self.status}"

# 📌 **Modelo de Eventos del Webhook**
class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, verbose_name="Tenant")
    event_id = models.CharField(max_length=100, verbose_name="ID del Evento")
    event_type = models.CharField(max_length=50, verbose_name="Tipo de Evento")
    payload = models.JSONField(verbose_name="Datos del Webhook")
    received_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Recepción")

    class Meta:
        verbose_name = "Evento del Webhook de WhatsApp"
        verbose_name_plural = "Eventos del Webhook de WhatsApp"

    def __str__(self):
        return f"Webhook {self.event_type} - {self.received_at}"

# 📌 **Modelo de Contactos de WhatsApp**
class WhatsAppContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="ID")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, verbose_name="Tenant")
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Phone Number")
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Name")
    profile_picture_url = models.URLField(blank=True, null=True, verbose_name="Profile Picture URL")
    wa_id = models.CharField(max_length=50, unique=True, verbose_name="WhatsApp ID")
    last_interaction = models.DateTimeField(auto_now=True, verbose_name="Last Interaction")
    last_policy_sent = models.DateTimeField(null=True, blank=True, verbose_name="Last Policy Sent")
    policy_accepted = models.BooleanField(default=False, verbose_name="Policy Accepted")
    last_message_before_policy = models.TextField(null=True, blank=True, verbose_name="Last Message Before Policy")
    first_buy = models.BooleanField(default=True, verbose_name="First Buy")

    class Meta:
        verbose_name = "WhatsApp Contact"
        verbose_name_plural = "WhatsApp Contacts"

    def __str__(self):
        return f"{self.name or 'Unknown'} - {self.phone_number}"

# 📌 **Modelo de Estado de Mensajes**
class MessageStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, verbose_name="Tenant")
    message = models.ForeignKey(
        WhatsAppMessage, on_delete=models.CASCADE, related_name="statuses", verbose_name="Mensaje"
    )
    status = models.CharField(
        max_length=50,
        choices=[("delivered", "Entregado"), ("read", "Leído"), ("failed", "Fallido")],
        verbose_name="Estado",
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")

    class Meta:
        verbose_name = "Estado de Mensaje"
        verbose_name_plural = "Estados de Mensajes"

    def __str__(self):
        return f"Estado {self.status} - {self.message.message_id}"
