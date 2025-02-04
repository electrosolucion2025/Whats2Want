from django.db import models
from apps.tenants.models import Tenant

# Modelo de Impresoras
class Printer(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    name = models.CharField(max_length=100)  # Nombre descriptivo de la impresora
    printer_type = models.CharField(max_length=50, choices=[
        ('beverages', 'Bebidas'),
        ('food', 'Comidas'),
    ])  # Tipo de impresora
    ip_address = models.GenericIPAddressField(blank=True, null=True)  # Dirección IP (si es de red)
    port = models.PositiveIntegerField(default=9100)  # Puerto de red (por defecto 9100)
    connection_type = models.CharField(max_length=50, choices=[
        ('usb', 'USB'),
        ('network', 'Red'),
        ('bluetooth', 'Bluetooth'),
    ])  # Tipo de conexión
    is_active = models.BooleanField(default=True)  # Estado de la impresora (activa o inactiva)
    location = models.CharField(max_length=100, blank=True, null=True)  # Ubicación física de la impresora
    last_maintenance = models.DateField(blank=True, null=True)  # Último mantenimiento
    created_at = models.DateTimeField(auto_now_add=True)  # Fecha de creación
    updated_at = models.DateTimeField(auto_now=True)  # Fecha de última actualización

    def __str__(self):
        return f'{self.name} ({self.printer_type})'
