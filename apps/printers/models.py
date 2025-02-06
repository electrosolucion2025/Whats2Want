import uuid

from django.db import models
from apps.tenants.models import Tenant

class PrinterZone(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, unique=True)  # Ejemplo: "COCINA", "BARRA"
    printer_ip = models.GenericIPAddressField()  # IP de la impresora
    printer_port = models.PositiveIntegerField(default=9100)  # Puerto estándar de impresión
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.printer_ip}"

class PrintTicket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="print_tickets")
    printer_zone = models.ForeignKey(PrinterZone, on_delete=models.CASCADE, related_name="tickets")  
    content = models.TextField()  # Contenido del ticket
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pendiente'),
        ('PRINTED', 'Impreso'),
        ('FAILED', 'Error'),
    ], default='PENDING')

    def __str__(self):
        return f"Ticket {self.printer_zone.name} - Pedido {self.order.order_number}"
    

