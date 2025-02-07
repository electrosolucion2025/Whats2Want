import base64
import json

from decimal import ROUND_HALF_UP, Decimal as D
from django.conf import settings
from django.urls import reverse
from redsys.client import RedirectClient
from redsys.constants import EUR, STANDARD_PAYMENT

class PaymentServiceRedsys:
    def __init__(self):
        self.client = RedirectClient(settings.REDSYS["SECRET_KEY"])

    def prepare_payment_request(self, order):
        """
        Prepara los parámetros para la pasarela de pago de Redsys.
        """
        redsys_config = settings.REDSYS

        # 🔢 Asegurar que el número del pedido tenga 12 dígitos
        order_number = str(order.order_number).zfill(12)

        parameters = {
            "merchant_code": redsys_config["MERCHANT_CODE"],
            "terminal": redsys_config["TERMINAL"],
            "transaction_type": STANDARD_PAYMENT,
            "currency": EUR,
            "order": order_number,
            "amount": D(order.total_price).quantize(D(".01"), ROUND_HALF_UP),
            "merchant_url": redsys_config["URL_NOTIFY"],
            "url_ok": f"{redsys_config['URL_OK']}{order.id}/",
            "url_ko": f"{redsys_config['URL_KO']}{order.id}/",
        }

        # Generar los parámetros con el cliente de Redsys
        request_data = self.client.prepare_request(parameters)

        # Decodificar los valores
        request_data["Ds_MerchantParameters"] = request_data["Ds_MerchantParameters"].decode()
        request_data["Ds_Signature"] = request_data["Ds_Signature"].decode()

        return request_data

def generate_payment_link(order):
    """
    Genera un link de pago de RedSys con los datos del pedido.
    """
    return f"https://e6f1-212-9-89-159.ngrok-free.app{reverse('redsys_redirect', args=[order.id])}"

def decode_redsys_parameters(merchant_parameters: str):
    """
    Decodifica los parámetros de pago de Redsys desde Base64.
    :param merchant_parameters: Cadena Base64 de Redsys.
    :return: Diccionario con los datos decodificados.
    """
    try:
        # Decodificar Base64 a JSON
        decoded_params = base64.b64decode(merchant_parameters).decode("utf-8")
        return json.loads(decoded_params)
    except Exception as e:
        print(f"❌ Error al decodificar los parámetros de Redsys: {e}", flush=True)
        return {}