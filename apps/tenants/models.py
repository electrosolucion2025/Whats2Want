import uuid

from django.db import models

# Modelo de Inquilinos (Tenant)
class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)  # Nombre de la empresa o cafetería
    owner_name = models.CharField(max_length=100)  # Nombre del propietario
    phone_number = models.CharField(max_length=20)  # Teléfono de contacto
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
