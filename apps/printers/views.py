from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from apps.printers.models import PrintTicket
from apps.tenants.models import Tenant

@csrf_exempt
def get_tickets_for_printing(request):
    """
    Endpoint que devuelve los tickets pendientes de impresión para un tenant específico.
    """
    try:
        phone_number_id = request.GET.get("phone_number_id")
        print(f"📥 Recibida solicitud con phone_number_id: {phone_number_id}", flush=True)

        if not phone_number_id:
            print("❌ Falta el parámetro 'phone_number_id'", flush=True)
            return JsonResponse({"status": "error", "message": "Falta phone_number_id"}, status=400)

        # 📌 Buscar el Tenant correspondiente
        tenant = Tenant.objects.filter(phone_number_id=phone_number_id).first()
        if not tenant:
            print(f"❌ Tenant no encontrado para phone_number_id: {phone_number_id}", flush=True)
            return JsonResponse({"status": "error", "message": "Tenant no encontrado"}, status=404)

        print(f"✅ Tenant encontrado: {tenant.name} (ID: {tenant.id})", flush=True)

        # 📌 Filtrar tickets SOLO de ese tenant
        tickets = PrintTicket.objects.filter(status="PENDING", tenant=tenant)
        print(f"🔍 Tickets encontrados: {tickets.count()}", flush=True)

        if not tickets.exists():
            print("⚠️ No hay tickets pendientes.", flush=True)
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

        print(f"📤 Enviando {len(response_data)} tickets para impresión.", flush=True)
        return JsonResponse({"status": "success", "tickets": response_data}, safe=False)

    except Exception as e:
        print(f"❌ Error en get_tickets_for_printing: {e}", flush=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def mark_ticket_as_printed(request):
    """
    Marca un ticket como impreso en la base de datos.
    """
    import json
    try:
        data = json.loads(request.body)
        ticket_id = data.get("ticket_id")

        if not ticket_id:
            return JsonResponse({"status": "error", "message": "Falta ticket_id"}, status=400)

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
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "JSON inválido"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)