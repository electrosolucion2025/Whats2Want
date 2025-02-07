import os
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import get_object_or_404
from apps.printers.models import PrinterZone, PrintTicket
from apps.tenants.models import Tenant

# 📌 **Admin de Printer Zones**
@admin.register(PrinterZone)
class PrinterZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "printer_ip", "printer_port", "active")
    list_filter = ("tenant", "active")
    search_fields = ("name", "printer_ip", "tenant__name")
    ordering = ("name",)
    list_editable = ("active",)

# 📌 **Admin de Print Tickets**
@admin.register(PrintTicket)
class PrintTicketAdmin(admin.ModelAdmin):
    list_display = ("order", "printer_zone", "tenant", "status", "created_at")
    list_filter = ("tenant", "printer_zone", "status", "created_at")  # ✅ Filtrar por Tenant
    search_fields = ("order__order_number", "printer_zone__name", "tenant__name")
    ordering = ("-created_at",)

    actions = ["reprint_selected_tickets", "mark_as_printed", "download_ticket_content"]

    def reprint_selected_tickets(self, request, queryset):
        """
        Marca los tickets seleccionados como "Pendiente" para que vuelvan a imprimirse.
        """
        count = queryset.update(status="PENDING")
        self.message_user(request, f"🔄 {count} ticket(s) marcados para reimpresión.", messages.SUCCESS)

    reprint_selected_tickets.short_description = "🔄 Reimprimir Tickets Seleccionados"

    def mark_as_printed(self, request, queryset):
        """
        Marca los tickets seleccionados como "Impresos".
        """
        count = queryset.update(status="PRINTED")
        self.message_user(request, f"✅ {count} ticket(s) marcados como impresos.", messages.SUCCESS)

    mark_as_printed.short_description = "✅ Marcar como Impreso"

    def download_ticket_content(self, request, queryset):
        """
        Permite descargar el contenido de los tickets seleccionados en un archivo .txt.
        """
        if queryset.count() == 1:
            ticket = queryset.first()
            filename = f"Ticket_{ticket.order.order_number}_{ticket.printer_zone.name}.txt"
            response = HttpResponse(ticket.content, content_type="text/plain")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        else:
            temp_filename = "tickets_batch.txt"
            with open(temp_filename, "w", encoding="utf-8") as file:
                for ticket in queryset:
                    file.write(f"Ticket para Pedido #{ticket.order.order_number}\n")
                    file.write(f"Zona de impresión: {ticket.printer_zone.name}\n")
                    file.write(f"Estado: {ticket.status}\n")
                    file.write(f"Contenido:\n{ticket.content}\n")
                    file.write("=" * 40 + "\n\n")

            with open(temp_filename, "rb") as file:
                response = HttpResponse(file.read(), content_type="text/plain")
                response["Content-Disposition"] = 'attachment; filename="tickets_batch.txt"'

            os.remove(temp_filename)  # Eliminar el archivo temporal después de la descarga
            return response

    download_ticket_content.short_description = "📥 Descargar Ticket(s) como .txt"
