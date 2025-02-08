import uuid
from django.db import models
from apps.orders.models import Order
from apps.tenants.models import Tenant

class PrinterZone(models.Model):
    """
    Represents a printing zone within a tenant, associated with a specific printer.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, verbose_name="Tenant")
    name = models.CharField(max_length=50, unique=True, verbose_name="Printer Zone Name")  # Example: "KITCHEN", "BAR"
    printer_ip = models.GenericIPAddressField(verbose_name="Printer IP Address")  # IP Address of the printer
    printer_port = models.PositiveIntegerField(default=9100, verbose_name="Printer Port")  # Default printing port
    active = models.BooleanField(default=True, verbose_name="Active?")

    class Meta:
        verbose_name = "Printer Zone"
        verbose_name_plural = "Printer Zones"
        ordering = ["name"]  # Order by name

    def __str__(self):
        return f"{self.name} - {self.printer_ip}"


class PrintTicket(models.Model):
    """
    Stores ticket printing details, including the associated order and printer.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PRINTED', 'Printed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, verbose_name="Tenant")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="print_tickets", verbose_name="Order")
    printer_zone = models.ForeignKey(
        PrinterZone, on_delete=models.CASCADE, related_name="tickets", verbose_name="Printer Zone"
    )
    content = models.TextField(verbose_name="Ticket Content")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Print Status")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = "Print Ticket"
        verbose_name_plural = "Print Tickets"
        ordering = ["-created_at"]  # Order by latest tickets

    def __str__(self):
        return f"Ticket {self.printer_zone.name} - Order {self.order.order_number}"
