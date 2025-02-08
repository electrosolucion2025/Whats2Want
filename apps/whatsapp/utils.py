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