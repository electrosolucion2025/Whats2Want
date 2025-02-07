from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from apps.printers.models import PrintTicket

@csrf_exempt
def get_tickets_for_printing(request):
    """
    Endpoint que devuelve los tickets pendientes de impresión.
    """
    try:
        tickets = PrintTicket.objects.filter(status="PENDING")

        if not tickets.exists():
            return JsonResponse({"status": "no_tickets"}, status=404)

        response_data = [
            {
                "id": str(ticket.id),
                "order_number": ticket.order.order_number,
                "printer_ip": ticket.printer_zone.printer_ip,
                "printer_port": ticket.printer_zone.printer_port,
                "content": ticket.content
            }
            for ticket in tickets
        ]

        return JsonResponse({"status": "success", "tickets": response_data}, safe=False)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def mark_ticket_as_printed(request):
    """
    Marca un ticket como impreso en la base de datos.
    """
    import json
    data = json.loads(request.body)

    ticket_id = data.get("ticket_id")
    try:
        ticket = PrintTicket.objects.get(id=ticket_id)
        ticket.status = "PRINTED"
        ticket.updated_at = now()
        ticket.save(update_fields=["status", "updated_at"])
        
        # 📌 **Verificar si TODOS los tickets del pedido han sido impresos**
        order = ticket.order
        remaining_tickets = order.print_tickets.filter(status="PENDING").exists()

        if not remaining_tickets:
            order.printer_status = "PRINTED"  # ✅ **Todos los tickets impresos**
            order.save()
        
        return JsonResponse({"status": "success", "message": "Ticket marcado como impreso"})
    except PrintTicket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Ticket no encontrado"}, status=404)