from datetime import datetime
import unicodedata
import uuid

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import PaymentServiceRedsys, decode_redsys_parameters, generate_payment_link
from apps.printers.models import PrintTicket
from apps.whatsapp.utils import send_whatsapp_message

def redsys_payment_redirect(request, order_id):
    """
    Genera el formulario para Redsys y lo envía automáticamente.
    """
    order = get_object_or_404(Order, id=order_id)
    redsys_service = PaymentServiceRedsys()
    payment_request = redsys_service.prepare_payment_request(order)
    
    return render(request, "payments/redsys_form.html", {
        "redsys_url": settings.REDSYS["URL_REDSYS"],
        "params": payment_request["Ds_MerchantParameters"],
        "signature": payment_request["Ds_Signature"]
    })

@csrf_exempt
def redsys_notify(request):
    """
    Procesa la notificación de Redsys y actualiza la base de datos.
    """
    try:
        print("🔵 Entrando en redsys_notify", flush=True)
        print(f"📥 Request Body: {request.body}", flush=True)
        print(f"📥 Request POST: {request.POST}", flush=True)
        # ✅ Obtener datos de Redsys desde POST
        merchant_parameters = request.POST.get("Ds_MerchantParameters")
        signature = request.POST.get("Ds_Signature")

        if not merchant_parameters or not signature:
            return JsonResponse({"error": "Datos de Redsys incompletos"}, status=400)

        print(f"🔍 Datos recibidos de Redsys: {merchant_parameters}", flush=True)

        # 🔍 Decodificar parámetros de Redsys
        decoded_parameters = decode_redsys_parameters(merchant_parameters)

        if not decoded_parameters:
            print("❌ Error: Parámetros decodificados son None", flush=True)
            return JsonResponse({"error": "No se pudieron decodificar los parámetros de Redsys"}, status=400)

        print(f"✅ Parámetros decodificados: {decoded_parameters}", flush=True)

        order_id = decoded_parameters.get("Ds_Order")
        response_code = int(decoded_parameters.get("Ds_Response", -1))

        if not order_id:
            print("❌ Error: Ds_Order no encontrado en la respuesta de Redsys", flush=True)
            return JsonResponse({"error": "No se encontró el ID del pedido en la notificación"}, status=400)

        # 🔎 Buscar el pago en la BD
        try:
            payment = Payment.objects.get(payment_id=order_id)
        except Payment.DoesNotExist:
            print(f"❌ Error: No se encontró un pago con ID {order_id}", flush=True)
            return JsonResponse({"error": "Pago no encontrado"}, status=404)

        if 0 <= response_code <= 99:  # ✅ **Pago exitoso**
            payment.status = "completed"
            payment.authorization_code = decoded_parameters.get("Ds_AuthorisationCode")
            payment.response_code = str(response_code)
            payment.card_last_digits = decoded_parameters.get("Ds_Card_Number")[-4:] if "Ds_Card_Number" in decoded_parameters else None
            payment.save()

            # 📝 **Actualizar el estado del pedido**
            order = payment.order
            order.payment_status = "PAID"
            order.status = "CONFIRMED"
            order.save()
            
            # 🖨️ **Generar los tickets de impresión**
            process_successful_payment(order)
            print(f"🖨️ Tickets de impresión generados para el pedido {order.order_number}", flush=True)

            # 📩 **Enviar mensaje de confirmación al usuario**
            confirmation_message = (
                f"✅ Tu pago ha sido recibido con éxito.\n"
                f"📌 Pedido: {order.order_number}\n"
                f"💰 Total: {payment.amount}€\n"
                f"📦 Tu pedido está en preparación. ¡Gracias por tu compra! 😊"
            )
            send_whatsapp_message(order.phone_number, confirmation_message, tenant=order.tenant)

            print(f"✅ Pago exitoso para el pedido {order.id}", flush=True)
            return JsonResponse({"status": "success", "message": "Pago confirmado"})

        else:  # ❌ **Pago fallido**
            payment.status = "failed"
            payment.response_code = str(response_code)
            payment.save()

            # 🔴 **Actualizar el estado del pedido original a "FAILED"**
            old_order = payment.order
            old_order.status = "FAILED"
            old_order.payment_status = "FAILED"
            old_order.save()

            # 🔄 **Clonar el pedido con un nuevo número de pedido**
            new_order_number = str(uuid.uuid4().int)[:12]

            new_order = Order.objects.create(
                tenant=old_order.tenant,
                phone_number=old_order.phone_number,
                chat_session=old_order.chat_session,
                table_number=old_order.table_number,
                notes=old_order.notes,
                order_number=new_order_number,
                status='PENDING',  # Nuevo pedido en estado pendiente
                delivery_type=old_order.delivery_type,
                payment_status='PENDING',
                discount=old_order.discount,
                tax_amount=old_order.tax_amount,
                is_scheduled=old_order.is_scheduled,
                total_price=old_order.total_price,
            )

            # 🔄 **Clonar los items del pedido (con related_name='items')**
            for item in old_order.items.all():  # 🔥 FIX AQUÍ 🔥
                OrderItem.objects.create(
                    tenant=item.tenant,
                    order=new_order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.price,
                    exclusions=item.exclusions,
                    special_instructions=item.special_instructions,
                    extras=item.extras,
                    discount=item.discount,
                    tax_amount=item.tax_amount
                )

            # 🏦 **Crear un nuevo registro de pago para el nuevo pedido**
            new_payment = Payment.objects.create(
                tenant=new_order.tenant,
                order=new_order,  # 🔥 Asociamos el nuevo pago al nuevo pedido
                payment_id=new_order_number,  # 🔥 Nuevo número de pedido como ID de pago
                amount=new_order.total_price,
                status="pending",
            )

            # 📦 **Generar un nuevo link de pago**
            new_payment_link = generate_payment_link(new_order)

            # 📩 **Enviar mensaje de error al usuario con el nuevo link**
            failure_message = (
                f"❌ Tu pago no se ha completado.\n"
                f"📌 Nuevo Pedido: {new_order.order_number}\n"
                f"💰 Total: {new_payment.amount}€\n"
                f"📩 Inténtalo de nuevo con este enlace: {new_payment_link}"
            )
            send_whatsapp_message(new_order.phone_number, failure_message, tenant=new_order.tenant)

            print(f"❌ Pago fallido, pedido marcado como 'FAILED', generado nuevo pedido y link para el usuario {new_order.id}", flush=True)
            return JsonResponse({"status": "failed", "message": "Pago rechazado, se generó un nuevo link"})


    except Exception as e:
        print(f"❌ Error procesando notificación de Redsys: {e}", flush=True)
        return JsonResponse({"error": str(e)}, status=500)

def redsys_success(request, order_id):
    """ Endpoint cuando el pago es exitoso """
    print(f"✅ Pago exitoso para el pedido {order_id}", flush=True)
    return JsonResponse({"message": "Pago completado con éxito."}, status=200)

def redsys_failure(request, order_id):
    """ Endpoint cuando el pago ha fallado """
    print(f"❌ Pago fallido para el pedido {order_id}", flush=True)
    return JsonResponse({"message": "El pago ha sido rechazado."}, status=400)

def process_successful_payment(order):
    """
    Genera los tickets de impresión después de que el pago ha sido confirmado.
    """
    print(f"✅ Generando tickets de impresión para el pedido {order.order_number}")

    # Obtener las zonas de impresión únicas para los productos del pedido
    printer_zones = set()
    for item in order.items.all():
        printer_zones.update(item.product.print_zones.all())  # M2M relation

    # Crear un ticket de impresión para cada zona
    tickets = []
    for zone in printer_zones:
        ticket_content = generate_ticket_content(order, zone)
        tickets.append(PrintTicket(
            tenant=order.tenant,
            order=order,
            printer_zone=zone,
            content=ticket_content,
            status="PENDING"
        ))

    # Guardar todos los tickets en la BD de una vez
    with transaction.atomic():
        PrintTicket.objects.bulk_create(tickets)

    print(f"🖨️ Se generaron {len(tickets)} tickets para el pedido {order.order_number}")
    
EMOJI_REPLACEMENTS = {
    "🌟": "*",
    "📅": "Fecha:",
    "🖨️": "Zona:",
    "📌": "Pedido:",
    "📦": "Productos:",
    "🥤": "[BEBIDAS]",
    "🍽️": "[COMIDA]",
    "✅": "[OK]",
    "❌": "[NO]",
    "⚠️": "[!]",
    "📢": "Atención:"
}

def generate_ticket_content(order, printer_zone):
    """
    Genera el contenido del ticket según la zona de impresión, evitando caracteres no imprimibles.
    """

    # Obtener fecha y hora actual para la impresión
    timestamp = datetime.now().strftime("%d/%m/%Y - %H:%M")

    # Encabezado del ticket
    ticket_lines = [
        clean_text("Restaurante El Mundo del Campero"),
        clean_text(f"Fecha: {timestamp}"),
        clean_text(f"Zona: {printer_zone.name}"),
        "=" * 32,
        clean_text(f"Pedido: #{order.order_number}"),
        clean_text(f"Teléfono: {order.phone_number}"),
    ]

    # Si el pedido tiene número de mesa, lo agregamos
    if order.table_number:
        ticket_lines.append(clean_text(f"Mesa: {order.table_number}"))

    ticket_lines.append("=" * 32)

    # Dividir productos en bebidas y comida
    bebidas = []
    comida = []

    for item in order.items.all():
        if printer_zone in item.product.print_zones.all():
            item_text = clean_text(f"{item.quantity}x {item.product.name}")

            if item.extras:
                item_text += clean_text("\n  + Extras: " + ", ".join([extra['name'] for extra in item.extras]))

            if item.exclusions:
                item_text += clean_text("\n  - [NO]: " + ", ".join(item.exclusions))

            if item.special_instructions:
                item_text += clean_text("\n  ! [!] " + item.special_instructions)

            # Separar bebidas y comida
            if "Bebida" in item.product.category.name or "Refresco" in item.product.category.name:
                bebidas.append(item_text)
            else:
                comida.append(item_text)

    # Sección de bebidas
    if bebidas:
        ticket_lines.append(clean_text("[BEBIDAS]"))
        ticket_lines.extend(bebidas)
        ticket_lines.append("-" * 32)

    # Sección de comida
    if comida:
        ticket_lines.append(clean_text("[COMIDA]"))
        ticket_lines.extend(comida)
        ticket_lines.append("-" * 32)

    # Estado del pago
    if order.payment_status == "PAID":
        ticket_lines.append(clean_text("[OK] PAGO CONFIRMADO"))
    else:
        ticket_lines.append(clean_text("[NO] PAGO PENDIENTE"))

    ticket_lines.append("=" * 32)
    ticket_lines.append(clean_text("Atencion: ¡Gracias por tu pedido!"))

    return "\n".join(ticket_lines)

def clean_text(text):
    """
    Convierte texto a ASCII seguro para evitar caracteres no imprimibles.
    - Elimina tildes.
    - Sustituye emojis por texto plano.
    """
    # Eliminar acentos/tildes
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

    # Reemplazar emojis por texto simple (si tienes un diccionario definido)
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        text = text.replace(emoji, replacement)

    return text

# def generate_ticket_content(order, printer_zone):
#     """
#     Genera el contenido del ticket según la zona de impresión.
#     """
#     ticket_lines = [f"Pedido #{order.order_number}", "-" * 30]

#     for item in order.items.all():
#         if printer_zone in item.product.print_zones.all():
#             ticket_lines.append(f"{item.quantity}x {item.product.name}")

#             # Extras
#             if item.extras:
#                 ticket_lines.append(f"  + Extras: {', '.join([extra['name'] for extra in item.extras])}")

#             # Exclusiones
#             if item.exclusions:
#                 ticket_lines.append(f"  - Sin: {', '.join(item.exclusions)}")

#             # Instrucciones especiales
#             if item.special_instructions:
#                 ticket_lines.append(f"  ! {item.special_instructions}")

#     ticket_lines.append("-" * 30)
#     return "\n".join(ticket_lines)