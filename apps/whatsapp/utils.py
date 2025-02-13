import json
import tempfile
import openai
import requests

from django.conf import settings


openai.api_key = settings.OPENAI_API_KEY
client = openai.Client(
    api_key=settings.OPENAI_API_KEY,
)


def send_whatsapp_message(to_phone_number, ai_response, tenant):
    url = f"https://graph.facebook.com/v22.0/{tenant.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {tenant.whatsapp_access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",    
        "recipient_type": "individual",
        "to": to_phone_number,
        "type": "text",
        "text": {
            "body": ai_response
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def send_policy_interactive_message(phone_number, tenant):
    """
    Envía un mensaje interactivo en WhatsApp para que el usuario acepte o rechace la política de privacidad.
    """
    url = f"https://graph.facebook.com/v22.0/{tenant.phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {tenant.whatsapp_access_token}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "text",
                "text": "Política de Privacidad"
            },
            "body": {
                "text": "Para continuar, debes aceptar nuestra política de privacidad:\n\n🔗 Política de Privacidad \nhttps://politicas-y-derechos-de-uso.up.railway.app\n\n¿Aceptas nuestros términos?"
            },
            "footer": {
                "text": "Whats2Want Services"
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "policy_accept", "title": "✅ Acepto"}},
                    {"type": "reply", "reply": {"id": "policy_decline", "title": "❌ No Acepto"}}
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        print("✅ Mensaje interactivo enviado correctamente")
    else:
        print(f"❌ Error al enviar mensaje interactivo: {response.text}")

def download_whatsapp_media(media_id, tenant):
    """Descargar archivos multimedia de WhatsApp"""
    url = f"https://graph.facebook.com/v22.0/{media_id}"
    headers = {
        "Authorization": f"Bearer {tenant.whatsapp_access_token}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        media_url = response.json().get('url')
        
        # 📌 Descargar el archivo real
        media_response = requests.get(media_url, headers=headers)
        if media_response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
                temp_audio.write(media_response.content)
                return temp_audio.name
            
        return None
    
def transcribe_audio(audio_path):
    """ Transcribe un archivo de audio usando OpenAI Whisper """
    try:
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
            
            return response.text
    except Exception as e:
        return f"Error en la transcripción: {str(e)}"

def mark_message_as_read(message_id, tenant):
    url = f"https://graph.facebook.com/v22.0/{tenant.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {tenant.whatsapp_access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Error al marcar como leído: {response.text}")
    else:
        print(f"✅ Mensaje {message_id} marcado como leído.")
        
def send_promotion_opt_in_message(phone_number, tenant):
    """
    Envía un mensaje interactivo preguntando si el usuario quiere recibir promociones.
    """
    print(f"🔹 Enviando mensaje interactivo de promoción a {phone_number}", flush=True)

    url = f"https://graph.facebook.com/v22.0/{tenant.phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {tenant.whatsapp_access_token}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "text",
                "text": "🎉 ¡Gracias por tu primera compra!"
            },
            "body": {
                "text": "¿Te gustaría recibir ofertas y promociones exclusivas con descuentos especiales?"
            },
            "footer": {
                "text": "Whats2Want Services"
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "promotions_accept", "title": "✅ Sí, quiero ofertas"}},
                    {"type": "reply", "reply": {"id": "promotions_decline", "title": "❌ No, gracias"}}
                ]
            }
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        print("✅ Mensaje interactivo de promociones enviado correctamente")
    else:
        print(f"❌ Error al enviar mensaje interactivo de promociones: {response.text}")