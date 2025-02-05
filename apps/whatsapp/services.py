from django.utils import timezone
from django.utils.timezone import make_aware
from datetime import datetime

from apps.chat.services import process_whatsapp_message
from .models import Tenant, WebhookEvent, WhatsAppContact, WhatsAppMessage

def process_webhook_event(data):
    # 1️⃣ Obtener el número de teléfono receptor del webhook
    phone_number = data.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('metadata', {}).get('display_phone_number')
    
    # 2️⃣ Obtener el Tenant asociado a ese número
    try:
        tenant = Tenant.objects.get(phone_number=phone_number)
        
    except Tenant.DoesNotExist:
        raise ValueError('Tenant no encontrado para el número de teléfono')
    
    # 3️⃣ Guardar el evento del webhook
    webhook_event = create_webhook_event(data, tenant)
    
    # 4️⃣ Procesar cada cambio recibido
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            contacts = value.get('contacts', [])
            messages = value.get('messages', [])
            
            # Guardar contactos
            for contact in contacts:
                whatsapp_contact = save_or_update_contact(contact, tenant)
                
                # Guardar mensajes asociados al contacto
                for message in messages:
                    save_message(message, tenant, phone_number)
                    
                    # 🚀 Procesar el mensaje para gestionar la sesión de chat
                    process_whatsapp_message(message, whatsapp_contact, tenant)

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
    
    WhatsAppMessage.objects.create(
        message_id=message_id,
        from_number=message_from,
        to_number=phone_number,
        message_type=message_type,
        content=content,
        status='delivered',
        direction='inbound',
        timestamp=timestamp,
        tenant=tenant
    )

def create_webhook_event(data, tenant):
    return WebhookEvent.objects.create(
        event_type=data.get('object'),
        payload=data,
        tenant=tenant
    )
