import os
import re
import uuid
from datetime import datetime

from django.utils import timezone
from django.utils.timezone import make_aware, now

from .models import Tenant, WebhookEvent, WhatsAppContact, WhatsAppMessage
from apps.assistant.services import generate_openai_response
from apps.chat.services import process_whatsapp_message
from apps.whatsapp.utils import (
    download_whatsapp_media,
    mark_message_as_read,
    send_policy_interactive_message,
    send_whatsapp_message,
    transcribe_audio,
)

def process_webhook_event(data):
    # 🔹 Validaciones iniciales
    entry_list = data.get("entry", [])
    if not entry_list:
        print("❌ Error: 'entry' no encontrado en el JSON o está vacío", flush=True)
        return

    changes_list = entry_list[0].get("changes", [])
    if not changes_list:
        print("❌ Error: 'changes' no encontrado en el JSON o está vacío", flush=True)
        return

    value_data = changes_list[0].get("value", {})
    if not value_data:
        print("❌ Error: 'value' no encontrado en 'changes'", flush=True)
        return

    metadata = value_data.get("metadata", {})
    if not metadata:
        print("❌ Error: 'metadata' no encontrado en 'value'", flush=True)
        return

    # 1️⃣ Obtener el número de teléfono receptor del webhook
    business_phone_number = metadata.get('display_phone_number')

    # 2️⃣ Obtener el Tenant asociado a ese número
    try:
        tenant = Tenant.objects.get(phone_number=business_phone_number)
    except Tenant.DoesNotExist:
        raise ValueError('Tenant no encontrado para el número de teléfono')

    # 3️⃣ Guardar el evento del webhook
    webhook_event = create_webhook_event(data, tenant)

    # 4️⃣ Procesar cada cambio recibido
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            
            if 'messages' in value:
                contacts = value.get('contacts', [])
                messages = value.get('messages', [])

                for contact in contacts:
                    whatsapp_contact = save_or_update_contact(contact, tenant)

                    for message in messages:
                        message_type = message.get('type')
                        transcribed_text = None
                        original_message_text = message.get('text', {}).get('body')  # 🔥 Guardamos el mensaje original

                        # 🔥 Si el mensaje es una interacción de botón
                        if message_type == 'interactive':
                            interactive_type = message.get('interactive', {}).get('type')

                            if interactive_type == 'button_reply':
                                button_id = message.get('interactive', {}).get('button_reply', {}).get('id')

                                if button_id == 'policy_accept':
                                    # ✅ Guardamos la aceptación en la base de datos
                                    whatsapp_contact.policy_accepted = True
                                    whatsapp_contact.save(update_fields=["policy_accepted"])

                                    send_whatsapp_message(
                                        whatsapp_contact.phone_number,
                                        "✅ Gracias por aceptar nuestra política de privacidad. Enseguida te atenderemos.",
                                        tenant
                                    )

                                    # 🚀 **Recuperamos el último mensaje guardado antes de enviar las políticas**
                                    last_saved_message = get_last_saved_message(whatsapp_contact)

                                    if last_saved_message:
                                        print("📩 Procesando el mensaje original después de aceptar políticas:", last_saved_message, flush=True)

                                        # ✅ **Creamos un mensaje igual al que WhatsApp envía**
                                        message = {
                                            "from": whatsapp_contact.phone_number,  # Número del usuario
                                            "id": str(uuid.uuid4()),  # ID ficticio para evitar duplicados
                                            "timestamp": int(now().timestamp()),  # Timestamp actual
                                            "text": {"body": last_saved_message},  # Mensaje original
                                            "type": "text"  # Tipo de mensaje
                                        }

                                elif button_id == 'policy_decline':
                                    send_whatsapp_message(
                                        whatsapp_contact.phone_number,
                                        "❌ Lo siento, no puedes continuar sin aceptar nuestra política de privacidad. Gracias por tu comprensión.",
                                        tenant
                                    )
                                    return  # 🚨 Detenemos el flujo aquí si rechaza
                                
                                elif button_id == 'promotions_accept':
                                    whatsapp_contact.accepts_promotions = True
                                    whatsapp_contact.save(update_fields=["accepts_promotions"])

                                    send_whatsapp_message(
                                        whatsapp_contact.phone_number,
                                        "🎊 ¡Genial! Te avisaremos sobre ofertas y promociones exclusivas. 🛍️✨",
                                        tenant
                                    )
                                    return
                                    
                                elif button_id == 'promotions_decline':
                                    whatsapp_contact.accepts_promotions = False
                                    whatsapp_contact.save(update_fields=["accepts_promotions"])

                                    send_whatsapp_message(
                                        whatsapp_contact.phone_number,
                                        "🙏 Gracias por tu respuesta. No te preocupes, siempre puedes cambiar de opinión.",
                                        tenant
                                    )
                                    return

                        # 🔥 Si el usuario aún NO ha aceptado las políticas, guardamos el mensaje y enviamos el mensaje interactivo
                        if not whatsapp_contact.policy_accepted:
                            print("📌 Guardando el mensaje original para cuando acepte políticas:", original_message_text, flush=True)
                            save_original_message(whatsapp_contact, original_message_text)  # 🛠️ Guardamos el mensaje original
                            send_policy_interactive_message(whatsapp_contact.phone_number, tenant)
                            return  # 🚨 IMPORTANTE: No procesamos más

                        # 🔥 Si el mensaje es un audio, descargar y transcribirlo
                        if message_type == 'audio':
                            audio_id = message.get('audio', {}).get('id')
                            audio_path = download_whatsapp_media(audio_id, tenant)
                            
                            if audio_path:
                                transcribed_text = transcribe_audio(audio_path)
                                os.remove(audio_path)

                        # 🚀 Guardar el mensaje en la base de datos
                        new_message = save_message(message, tenant, business_phone_number, transcribed_text=transcribed_text)
                        
                        if new_message is None:
                            print("⚠️ Mensaje duplicado detectado. No se procesará nuevamente.")
                            continue
                        
                        # 🚀 Procesar el mensaje para gestionar la sesión de chat
                        assistant_session = process_whatsapp_message(
                            message, whatsapp_contact, tenant, transcribed_text=transcribed_text
                        )
                        
                        # 🚀 Generar la respuesta de OpenAI
                        ai_response = generate_openai_response(
                            message, assistant_session, whatsapp_contact, transcribed_text=transcribed_text
                        )
                        
                        ai_response_sanitized = sanitize_ai_response(ai_response)
                        
                        # 🚀 Enviar la respuesta a WhatsApp
                        send_whatsapp_message(whatsapp_contact.phone_number, ai_response_sanitized, tenant)
                        
                        # 🚀 Actualizar el mensaje como leído
                        mark_message_as_read(message.get('id'), tenant)
                        
def save_original_message(contact, message_text):
    """Guarda el último mensaje antes de enviar la política."""
    print("🔥🔥🔥🔥🔥 save_original_message", message_text, flush=True)
    if message_text:
        contact.last_message_before_policy = message_text
        contact.save(update_fields=["last_message_before_policy"])
        
def get_last_saved_message(contact):
    """Obtiene el último mensaje guardado antes de la política y lo borra después de usarlo."""
    last_message = contact.last_message_before_policy
    contact.last_message_before_policy = None  # 🔥 Borramos el mensaje después de usarlo
    contact.save(update_fields=["last_message_before_policy"])
    return last_message

def save_or_update_contact(contact, tenant):
    wa_id = contact.get('wa_id')
    name = contact.get('profile', {}).get('name')
    
    whatsapp_contact, created = WhatsAppContact.objects.get_or_create(
        wa_id=wa_id,
        defaults={
            'name': name,
            'tenant': tenant,
            'phone_number': wa_id,
            'last_interaction': timezone.now()
        }
    )
    
    if not created:
        whatsapp_contact.name = name
        whatsapp_contact.last_interaction = timezone.now()
        whatsapp_contact.save()
    
    return whatsapp_contact

def save_message(message, tenant, phone_number, transcribed_text=None):
    """
    Guarda el mensaje de WhatsApp en la base de datos.
    Si es un mensaje de audio, almacena la transcripción en `content`.
    """
    message_id = message.get("id")
    message_from = message.get("from")
    message_type = message.get("type")
    timestamp = message.get("timestamp")
    
    # Verificar si el mensaje ya existe
    if WhatsAppMessage.objects.filter(message_id=message_id).exists():
        return None

    # Si el mensaje es de texto, extraer el contenido normal
    if message_type == "text":
        content = message.get("text", {}).get("body")
    elif message_type == "audio" and transcribed_text:
        content = transcribed_text  # Usar la transcripción como contenido del mensaje
    else:
        content = None  # Para otros tipos de mensajes que no manejamos ahora

    # Convertir timestamp a datetime
    timestamp = make_aware(datetime.fromtimestamp(int(timestamp)))

    new_message, _ = WhatsAppMessage.objects.get_or_create(
        message_id=message_id,
        defaults={
            "from_number": message_from,
            "to_number": phone_number,
            "message_type": message_type,
            "content": content,  # Aquí guardamos la transcripción si es un audio
            "status": "delivered",
            "direction": "inbound",
            "timestamp": timestamp,
            "tenant": tenant,
        },
    )
    
    return new_message

def create_webhook_event(data, tenant):
    return WebhookEvent.objects.create(
        event_type=data.get('object'),
        payload=data,
        tenant=tenant
    )

def sanitize_ai_response(response: str) -> str:
    # Lista de frases o palabras que queremos eliminar
    forbidden_phrases = [
        "Aquí tienes el resumen del pedido en formato JSON:",
        "Aquí tienes el resumen de tu pedido en formato JSON:",
        "Este es el resumen del pedido:",
        "JSON resultante:",
        "Aquí está el resultado en JSON:",
        "Resumen del pedido:",
        "Resultado:",
        "Salida JSON:"
    ]
    
    # Eliminar cada frase prohibida de la respuesta
    for phrase in forbidden_phrases:
        response = response.replace(phrase, "").strip()

    # Opcional: Eliminar líneas en blanco generadas por los reemplazos
    # response = re.sub(r'\n\s*\n', '\n', response)

    return response