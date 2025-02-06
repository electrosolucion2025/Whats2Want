import json
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import PaymentServiceRedsys, decode_redsys_parameters, generate_payment_link
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