from itertools import chain
import json
import threading
from turtle import width
import uuid

from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from escpos.printer import Network

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import PaymentServiceRedsys, decode_redsys_parameters, generate_payment_link
from apps.printers.models import PrintTicket
from apps.whatsapp.utils import send_promotion_opt_in_message, send_whatsapp_message
from apps.payments.utils import send_order_email
from apps.whatsapp.models import WhatsAppContact


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
            order.status = "COMPLETED"
            order.save()
            
                # 🚪 **Cerrar la sesión del usuario**
            chat_session = order.chat_session  # Asegurarnos de que el pedido tiene una sesión activa
            if chat_session:
                chat_session.is_active = False  # Marcar la sesión como cerrada
                chat_session.ended_at = timezone.now()  # Guardar la hora de cierre
                chat_session.save()
                print(f"🔒 Sesión {chat_session.id} cerrada tras el pago del pedido {order.order_number}", flush=True)
            
            # 🖨️ **Generar los tickets de impresión**
            threading.Thread(target=process_successful_payment, args=(order,), daemon=True).start()
            # process_successful_payment(order)
            print(f"🖨️ Tickets de impresión generados para el pedido {order.order_number}", flush=True)

            # 📩 **Enviar mensaje de confirmación al usuario**
            confirmation_message = (
                f"✅ Tu pago ha sido recibido con éxito.\n"
                f"📌 Pedido: {order.order_number}\n"
                f"💰 Total: {payment.amount}€\n"
                f"📦 Tu pedido está en preparación. ¡Gracias por tu compra! 😊"
            )
            send_whatsapp_message(order.phone_number, confirmation_message, tenant=order.tenant)

            send_order_email(order)  # 📧 Enviar correo con el ticket del pedido
            
            # 🔹 Obtener el `WhatsAppContact` usando el `phone_number` de la sesión
            try:
                whatsapp_contact = WhatsAppContact.objects.filter(phone_number=order.phone_number, tenants=order.tenant).first()

                # 🔹 Si no ha respondido sobre promociones, enviar mensaje interactivo
                if whatsapp_contact and whatsapp_contact.accepts_promotions is None:
                    send_promotion_opt_in_message(whatsapp_contact.phone_number, order.tenant)
                    
            except WhatsAppContact.DoesNotExist:
                print(f"⚠️ No se encontró un WhatsAppContact para el número {order.phone_number}", flush=True)
            
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

    # 🔍 **Obtener zonas de impresión únicas**
    try:
        printer_zones = {
            zone
            for item in order.items.all()
            for zone in chain(item.product.print_zones.all(), item.product.category.print_zones.all())
        }
    except Exception as e:
        print(f"❌ Error obteniendo zonas de impresión: {e}", flush=True)
        return False  # ❌ Si hay error, se interrumpe la impresión pero el flujo sigue

    if not printer_zones:
        print(f"⚠️ No hay zonas de impresión asignadas para el pedido {order.order_number}. No se generarán tickets.")
        return False  # 🔹 No hay zonas, no se imprime nada

    # 🖨️ **Generar tickets de impresión**
    tickets = []
    for zone in printer_zones:
        try:
            ticket_content = generate_ticket_content(order, zone)

            # 📌 **Evitar guardar tickets vacíos**
            if not ticket_content or not ticket_content.strip():
                print(f"⚠️ Ticket vacío para la zona '{zone.name}', omitiendo...")
                continue

            tickets.append(PrintTicket(
                tenant=order.tenant,
                order=order,
                printer_zone=zone,
                content=ticket_content,
                status="PENDING"
            ))

            print(f"🖨️ Ticket generado para la zona '{zone.name}'")

        except Exception as e:
            print(f"❌ Error generando ticket para la zona '{zone.name}': {e}", flush=True)

    # 📌 **Guardar tickets en la base de datos**
    if tickets:
        try:
            with transaction.atomic():
                PrintTicket.objects.bulk_create(tickets)
            print(f"✅ Se generaron {len(tickets)} tickets para el pedido {order.order_number}")
            return True  # ✅ Se imprimieron correctamente
        except Exception as e:
            print(f"❌ Error guardando los tickets en la base de datos: {e}", flush=True)
            return False  # ❌ Falló el guardado, pero el pedido sigue normal
    else:
        print(f"⚠️ No se generaron tickets válidos para el pedido {order.order_number}")
        return False  # 🔹 No hay tickets, pero el flujo sigue
    
def generate_ticket_content(order, printer_zone):
    """
    Genera el contenido del ticket en ESC/POS con diseño mejorado.
    """

    # 🔹 Configurar la impresora térmica
    printer_ip = printer_zone.printer_ip
    printer_port = printer_zone.printer_port

    try:
        try:
            p = Network(printer_ip, printer_port)
        except Exception as e:
            print(f"❌ Error al conectar a la impresora en {printer_ip}:{printer_port}: {e}")
            return ""
        
        # **Encabezado (Nombre del negocio grande)**
        p._raw(b'\x1B\x61\x01')  # 🔹 Centrar texto
        # p._raw(b'\x1D\x21\x11')  # 🔹 Doble altura y ancho
        p._raw(b'\x1D\x21\x01')  # 🔹 Doble altura
        p.text(" ".join(order.tenant.name.upper()) + "\n")  # 🔹 Agrega un espacio entre cada letra

        # **Separador**
        p._raw(b'\x1D\x21\x00')
        p._raw(b'\x1D\x21\x11')
        p.text("=" * 24 + "\n")
        p._raw(b'\x1D\x21\x00')  # 🔹 Volver a tamaño normal

        # **Fecha y zona (Doble ancho, altura normal)**
        p._raw(b'\x1B\x61\x00')  # 🔹 Alinear a la izquierda
        timestamp = datetime.now().strftime("%d/%m/%Y  %H:%M")
        p.text(f"Fecha: {timestamp}\n")
        p.text(f"Zona: {printer_zone.name.upper()}\n")

        # **Detalles del pedido**
        p.text(f"Pedido: #{order.order_number}\n")
        p.text(f"Teléfono: {order.phone_number}\n")
        if order.table_number:
            p.text(f"Mesa: {order.table_number}\n")

        # **Línea separadora**
        p._raw(b'\x1B\x61\x01')  # 🔹 Centrar
        p._raw(b'\x1D\x21\x11')  # 🔹 Doble altura y ancho
        p.text("-" * 24 + "\n")
        p._raw(b'\x1D\x21\x00')  # 🔹 Volver a tamaño normal

        # **Clasificar productos por zona de impresión**
        productos_en_zona = []

        for item in order.items.all():
            product = item.product
            product_zones = product.print_zones.all() or product.category.print_zones.all()

            # 🔍 **Verificar si el producto pertenece a la zona actual**
            if printer_zone in product_zones:
                item_text = f"{item.quantity}x {item.product.name} - {item.product.price:.2f} Euros"

                # ✅ **Formatear los extras en lista**
                if item.extras:
                    extras_text = "\n".join([f"  + {extra['name']} (+{extra['price']:.2f} Euros)" for extra in item.extras])
                    item_text += f"\n{extras_text}"  # Se agrega a la siguiente línea

                # ✅ **Formatear exclusiones en lista**
                if item.exclusions:
                    if isinstance(item.exclusions, str):
                        try:
                            exclusions_list = json.loads(item.exclusions)  # Convertir de JSON a lista
                        except json.JSONDecodeError:
                            exclusions_list = item.exclusions.split(",")  # Dividir por comas como fallback
                    else:
                        exclusions_list = item.exclusions or []  # Asegurar que sea una lista

                    exclusions_text = "\n".join([f"  - [SIN] {exclusion.strip()}" for exclusion in exclusions_list if exclusion])
                    item_text += f"\n{exclusions_text}"

                # ✅ **Formatear instrucciones especiales**
                if item.special_instructions:
                    item_text += f"\n  ! [NOTA]: {item.special_instructions.strip() if item.special_instructions else ''}"


                productos_en_zona.append(item_text)  # ✅ **Agregar solo productos de la zona actual**

        # 🔹 Si no hay productos para esta zona, no generamos ticket
        if not productos_en_zona:
            return ""

        # **Encabezado de la zona**
        p._raw(b'\x1B\x61\x00')  # 🔹 Alinear a la izquierda
        p._raw(b'\x1B\x45\x01')  # 🔹 Negrita ON
        p._raw(b'\x1D\x21\x01')  # 🔹 Doble altura
        p.text(f"[ {printer_zone.name.upper()} ]\n")  # 🔹 Imprimir la zona en el ticket
        p._raw(b'\x1D\x21\x00')  # 🔹 Volver a tamaño normal
        p._raw(b'\x1B\x45\x00')  # 🔹 Negrita OFF
        p._raw(b'\n')  # 🔹 Salto de línea

        # **Imprimir los productos en esta zona**
        for producto in productos_en_zona:
            p.text(producto + "\n")

        # **Línea final separadora**
        p._raw(b'\x1D\x21\x11')  # 🔹 Doble altura y ancho
        p.text("-" * 24 + "\n")
        p._raw(b'\x1D\x21\x00')  # 🔹 Volver a tamaño normal

        # **Estado del pago**
        p._raw(b'\x1B\x61\x01')  # 🔹 Centrar texto
        p._raw(b'\x1D\x21\x11')  # 🔹 Doble ancho y alto
        if order.payment_status == "PAID":
            p.text("[ PAGO CONFIRMADO ]\n")
        else:
            p.text("[ PAGO PENDIENTE ]\n")
        p._raw(b'\x1D\x21\x00')  # 🔹 Volver a tamaño normal

        # **Mensaje final**
        p._raw(b'\x1D\x21\x11')  # 🔹 Doble ancho y alto
        p.text("¡Gracias por tu pedido!\n")
        p._raw(b'\x1D\x21\x00')  # 🔹 Volver a tamaño normal

        p.text("\n\n\n")  # 🔹 Espacios extra

        # **Corte de papel**
        p._raw(b'\x1D\x56\x41\x10')  # 🔹 Corte parcial
        p._raw(b'\x1D\x56\x00')  # 🔹 Corte total si lo admite
        p.cut()
        p.close()

        print(f"✅ Ticket enviado correctamente a {printer_ip}:{printer_port}")

    except Exception as e:
        print(f"❌ Error al imprimir el ticket en {printer_ip}:{printer_port}: {e}")
