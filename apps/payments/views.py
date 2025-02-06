import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.services import PaymentServiceRedsys, decode_redsys_parameters
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

            # 📩 **Enviar mensaje de error al usuario**
            failure_message = (
                f"❌ Tu pago no se ha completado.\n"
                f"📌 Pedido: {payment.order.order_number}\n"
                f"💰 Total: {payment.amount}€\n"
                f"📩 Inténtalo de nuevo con este enlace: {payment.order.get_payment_link()}"
            )
            send_whatsapp_message(payment.order.phone_number, failure_message, tenant=payment.order.tenant)

            print(f"❌ Pago fallido para el pedido {order.id}", flush=True)
            return JsonResponse({"status": "failed", "message": "Pago rechazado"})

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