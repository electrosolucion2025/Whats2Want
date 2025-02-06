from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.orders.models import Order
from apps.payments.services import PaymentServiceRedsys

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

def redsys_notify(request):
    """ Endpoint para recibir la notificación de Redsys """
    print("🔔 Redsys ha enviado una notificación de pago.", flush=True)
    return JsonResponse({"status": "OK"}, status=200)

def redsys_success(request, order_id):
    """ Endpoint cuando el pago es exitoso """
    print(f"✅ Pago exitoso para el pedido {order_id}", flush=True)
    return JsonResponse({"message": "Pago completado con éxito."}, status=200)

def redsys_failure(request, order_id):
    """ Endpoint cuando el pago ha fallado """
    print(f"❌ Pago fallido para el pedido {order_id}", flush=True)
    return JsonResponse({"message": "El pago ha sido rechazado."}, status=400)