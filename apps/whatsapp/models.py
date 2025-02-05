import uuid

from django.db import models
from apps.tenants.models import Tenant

# Modelo de Mensajes de WhatsApp
class WhatsAppMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    message_id = models.CharField(max_length=100, unique=True)  # ID del mensaje proporcionado por WhatsApp
    from_number = models.CharField(max_length=20)  # Número del remitente
    to_number = models.CharField(max_length=20)  # Número del destinatario (empresa)
    message_type = models.CharField(max_length=50, choices=[
        ('text', 'Text'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('sticker', 'Sticker'),
        ('location', 'Location'),
    ])  # Tipo de mensaje
    content = models.TextField(blank=True, null=True)  # Contenido del mensaje (texto, URL, etc.)
    status = models.CharField(max_length=50, choices=[
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ], default='sent')  # Estado del mensaje
    direction = models.CharField(max_length=10, choices=[
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ])  # Dirección del mensaje (entrante o saliente)
    timestamp = models.DateTimeField(auto_now_add=True)  # Fecha y hora del mensaje

    def __str__(self):
        return f'Message {self.message_id} - {self.status}'

# Modelo de Eventos del Webhook
class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    event_id = models.CharField(max_length=100, unique=False)  # ID del evento de WhatsApp
    event_type = models.CharField(max_length=50)  # Tipo de evento (mensaje recibido, entregado, etc.)
    payload = models.JSONField()  # Datos completos del evento
    received_at = models.DateTimeField(auto_now_add=True)  # Fecha y hora de recepción del evento

    def __str__(self):
        return f'Event {self.event_id} - {self.event_type}'

# Modelo de Contactos de WhatsApp
class WhatsAppContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    phone_number = models.CharField(max_length=20, unique=True)  # Número del contacto
    name = models.CharField(max_length=100, blank=True, null=True)  # Nombre del contacto
    profile_picture_url = models.URLField(blank=True, null=True)  # Foto de perfil
    wa_id = models.CharField(max_length=50, unique=True)  # ID único de WhatsApp
    last_interaction = models.DateTimeField(auto_now=True)  # Se actualiza automáticamente

    def __str__(self):
        return self.phone_number

# Modelo de Estado de Mensajes
class MessageStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    message = models.ForeignKey(WhatsAppMessage, on_delete=models.CASCADE, related_name='statuses')  # Relación con el mensaje
    status = models.CharField(max_length=50, choices=[
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ])  # Estado del mensaje
    timestamp = models.DateTimeField(auto_now_add=True)  # Fecha y hora del cambio de estado

    def __str__(self):
        return f'Status {self.status} for {self.message.message_id}'
