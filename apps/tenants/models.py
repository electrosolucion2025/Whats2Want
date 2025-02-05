import uuid

from django.db import models

# Modelo de Inquilinos (Tenant)
class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)  # Nombre de la empresa o cafetería
    owner_name = models.CharField(max_length=100)  # Nombre del propietario
    phone_number = models.CharField(max_length=20)  # Teléfono de contacto
    phone_number_id = models.CharField(max_length=50, blank=True, null=True)  # Nuevo campo para el ID de WhatsApp Business
    whatsapp_access_token = models.CharField(max_length=255, blank=True, null=True)  # Token de acceso para WhatsApp
    email = models.EmailField()  # Correo electrónico
    address = models.TextField(blank=True, null=True)  # Dirección física
    nif = models.CharField(max_length=20, blank=True, null=True)  # Número de identificación fiscal
    timezone = models.CharField(max_length=50, default='UTC')  # Zona horaria
    currency = models.CharField(max_length=10, default='EUR')  # Moneda predeterminada
    is_active = models.BooleanField(default=True)  # Estado del inquilino
    created_at = models.DateTimeField(auto_now_add=True)  # Fecha de creación
    updated_at = models.DateTimeField(auto_now=True)  # Fecha de última actualización

    def __str__(self):
        return self.name

class TenantPrompt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='prompts')
    name = models.CharField(max_length=100, default='Prompt Principal')  # Nombre del prompt
    content = models.TextField()  # El contenido del prompt
    is_active = models.BooleanField(default=True)  # Para activar/desactivar prompts

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"