import requests

from datetime import datetime
from django.utils import timezone
from django.utils.timezone import make_aware

from .models import Tenant, WebhookEvent, WhatsAppContact, WhatsAppMessage
from apps.assistant.services import generate_openai_response
from apps.chat.services import process_whatsapp_message
from apps.whatsapp.utils import send_whatsapp_message

def process_webhook_event(data):
    # 1️⃣ Obtener el número de teléfono receptor del webhook
    business_phone_number = data.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('metadata', {}).get('display_phone_number')
    
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
                
                # Guardar contactos
                for contact in contacts:
                    whatsapp_contact = save_or_update_contact(contact, tenant)
                    
                    # Guardar mensajes asociados al contacto
                    for message in messages:
                        # 🚀 Guardar el mensaje en la base de datos
                        save_message(message, tenant, business_phone_number)
                        
                        # 🚀 Procesar el mensaje para gestionar la sesión de chat
                        assistant_session = process_whatsapp_message(message, whatsapp_contact, tenant)
                        
                        # 🚀 Generar la respuesta de OpenAI
                        ai_response = generate_openai_response(message, assistant_session)
                        
                        # 🚀 Enviar la respuesta a WhatsApp
                        send_whatsapp_message(whatsapp_contact.phone_number, ai_response, tenant)
                        
                        # 🚀 Actualizar el mensaje como leído
                        mark_message_as_read(message.get('id'), tenant)

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

def save_message(message, tenant, phone_number):
    message_id = message.get('id')
    message_from = message.get('from')
    message_type = message.get('type')
    timestamp = message.get('timestamp')
    content = message.get('text', {}).get('body')
    
    # Convertir timestamp a datetime
    timestamp = make_aware(datetime.fromtimestamp(int(timestamp)))
    
    # Verificar si el mensaje ya existe
    if WhatsAppMessage.objects.filter(message_id=message_id).exists():
        return
    
    WhatsAppMessage.objects.get_or_create(
        message_id=message_id,
        defaults = {
            'from_number': message_from,
            'to_number': phone_number,
            'message_type': message_type,
            'content': content,
            'status': 'delivered',
            'direction': 'inbound',
            'timestamp': timestamp,
            'tenant': tenant
        }
    )

def create_webhook_event(data, tenant):
    return WebhookEvent.objects.create(
        event_type=data.get('object'),
        payload=data,
        tenant=tenant
    )

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