import os
import uuid
from datetime import datetime

from django.utils.timezone import make_aware, now
from django.db import transaction

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
    """Procesa los eventos recibidos desde WhatsApp de manera eficiente."""
    
    # 🔹 Validaciones iniciales
    entry_list = data.get("entry")
    if not entry_list:
        print("❌ Error: 'entry' no encontrado en JSON", flush=True)
        return

    value_data = entry_list[0].get("changes", [{}])[0].get("value")
    if not value_data:
        print("❌ Error: 'value' no encontrado en 'changes'", flush=True)
        return

    business_phone_number = value_data.get("metadata", {}).get("display_phone_number")
    
    # 🔹 Obtener el Tenant asociado al número de WhatsApp
    tenant = Tenant.objects.filter(phone_number=business_phone_number).first()
    if not tenant:
        print(f"❌ Tenant no encontrado para {business_phone_number}", flush=True)
        return

    # 🔹 Guardar el evento en la base de datos (Evita bloqueos con transaction.atomic)
    with transaction.atomic():
        webhook_event = WebhookEvent.objects.create(
            event_type=data.get("object"), payload=data, tenant=tenant
        )

    # 🔹 Procesar mensajes entrantes
    for entry in entry_list:
        for change in entry.get("changes", []):
            value = change.get("value", {})

            if "messages" in value:
                contacts = {c["wa_id"]: c.get("profile", {}).get("name") for c in value.get("contacts", [])}
                messages = value.get("messages", [])

                # 🔹 Procesar cada mensaje
                for message in messages:
                    process_whatsapp_message_entry(message, contacts, tenant)


def process_whatsapp_message_entry(message, contacts, tenant):
    """Procesa un solo mensaje recibido de WhatsApp."""
    message_type = message.get("type")
    from_number = message.get("from")
    
    # 🔹 Buscar o crear el contacto
    whatsapp_contact, created = WhatsAppContact.objects.get_or_create(
        wa_id=from_number,
        defaults={
            "name": contacts.get(from_number),
            "tenant": tenant,
            "phone_number": from_number,
            "last_interaction": now()
        }
    )

    if not created:
        whatsapp_contact.last_interaction = now()
        whatsapp_contact.save(update_fields=["last_interaction"])

    # 🔹 Procesar interacciones de botones
    if message_type == "interactive":
        handle_interactive_message(message, whatsapp_contact, tenant)
        return

    # 🔹 Si aún NO aceptó la política, enviamos el mensaje de aceptación
    if not whatsapp_contact.policy_accepted:
        save_original_message(whatsapp_contact, message.get("text", {}).get("body"))
        send_policy_interactive_message(whatsapp_contact.phone_number, tenant)
        return

    # 🔹 Procesar mensaje de audio
    transcribed_text = None
    if message_type == "audio":
        transcribed_text = process_audio_message(message, tenant)

    # 🔹 Guardar el mensaje en la base de datos
    new_message = save_message(message, tenant, transcribed_text)
    if new_message is None:
        print("⚠️ Mensaje duplicado, ignorando...", flush=True)
        return

    # 🔹 Procesar el mensaje en la sesión del asistente
    assistant_session = process_whatsapp_message(message, whatsapp_contact, tenant, transcribed_text=transcribed_text)

    # 🔹 Generar y enviar la respuesta de OpenAI
    ai_response = sanitize_ai_response(generate_openai_response(message, assistant_session, whatsapp_contact, transcribed_text))
    send_whatsapp_message(whatsapp_contact.phone_number, ai_response, tenant)

    # 🔹 Marcar mensaje como leído
    mark_message_as_read(message.get("id"), tenant)


def handle_interactive_message(message, whatsapp_contact, tenant):
    """Procesa interacciones de botones en WhatsApp."""
    button_id = message.get("interactive", {}).get("button_reply", {}).get("id")

    responses = {
        "policy_accept": ("✅ Gracias por aceptar nuestra política. Enseguida te atenderemos.", True),
        "policy_decline": ("❌ No puedes continuar sin aceptar la política.", False),
        "promotions_accept": ("🎊 ¡Genial! Te avisaremos sobre promociones exclusivas. 🛍️✨", True),
        "promotions_decline": ("🙏 Gracias por tu respuesta. Siempre puedes cambiar de opinión.", False),
    }

    if button_id in responses:
        message_text, accepted = responses[button_id]
        
        if "policy" in button_id:
            whatsapp_contact.policy_accepted = accepted
        elif "promotions" in button_id:
            whatsapp_contact.accepts_promotions = accepted

        whatsapp_contact.save(update_fields=["policy_accepted", "accepts_promotions"])
        send_whatsapp_message(whatsapp_contact.phone_number, message_text, tenant)

        if button_id == "policy_accept":
            last_message = get_last_saved_message(whatsapp_contact)
            if last_message:
                process_whatsapp_message_entry(
                    {"from": whatsapp_contact.phone_number, "id": str(uuid.uuid4()), "timestamp": int(now().timestamp()), "text": {"body": last_message}, "type": "text"},
                    {whatsapp_contact.phone_number: whatsapp_contact.name},
                    tenant
                )
        return


def process_audio_message(message, tenant):
    """Descarga y transcribe un mensaje de audio."""
    audio_id = message.get("audio", {}).get("id")
    audio_path = download_whatsapp_media(audio_id, tenant)
    if audio_path:
        transcribed_text = transcribe_audio(audio_path)
        os.remove(audio_path)
        return transcribed_text
    return None


def save_message(message, tenant, transcribed_text=None):
    """Guarda un mensaje en la base de datos evitando duplicados."""
    message_id = message.get("id")
    if WhatsAppMessage.objects.filter(message_id=message_id).exists():
        return None

    message_data = {
        "from_number": message.get("from"),
        "to_number": tenant.phone_number,
        "message_type": message.get("type"),
        "content": message.get("text", {}).get("body") if message.get("type") == "text" else transcribed_text,
        "status": "delivered",
        "direction": "inbound",
        "timestamp": make_aware(datetime.fromtimestamp(int(message.get("timestamp")))),
        "tenant": tenant,
    }

    return WhatsAppMessage.objects.create(message_id=message_id, **message_data)


def sanitize_ai_response(response: str) -> str:
    """Elimina contenido no deseado en la respuesta de OpenAI."""
    forbidden_phrases = [
        "Aquí tienes el resumen del pedido en formato JSON:",
        "Este es el resumen del pedido:",
        "Resultado:",
    ]
    for phrase in forbidden_phrases:
        response = response.replace(phrase, "").strip()
    return response

def save_original_message(contact, message_text):
    """Guarda el último mensaje antes de enviar la política."""
    if message_text:
        contact.last_message_before_policy = message_text
        contact.save(update_fields=["last_message_before_policy"])


def get_last_saved_message(contact):
    """Obtiene el último mensaje guardado antes de la política y lo borra después de usarlo."""
    last_message = contact.last_message_before_policy
    contact.last_message_before_policy = None  # 🔥 Borramos el mensaje después de usarlo
    contact.save(update_fields=["last_message_before_policy"])
    return last_message
