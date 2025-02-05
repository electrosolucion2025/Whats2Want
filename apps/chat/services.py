


from datetime import timedelta
from django.utils.timezone import now

from apps.chat.models import ChatMessage, ChatSession


SESSION_TIMEOUT = timedelta(minutes=15) # Tiempo de inactividad para cerrar la sesión

def manage_chat_session(tenant, phone_number, message_content):
    # 1️⃣ Verificar si existe una sesión activa para el contacto
    active_session = ChatSession.objects.filter(
        tenant=tenant,
        phone_number=phone_number,
        is_active=True
    ).first()
    
    # 2️⃣ Verificar si la sesión está activa y no ha superado el tiempo de inactividad
    if active_session:
        if (now() - active_session.last_interaction) > SESSION_TIMEOUT:
            # La sesión ha superado el tiempo de inactividad
            active_session.is_active = False
            active_session.end_time = now()
            active_session.save()
            active_session = None
            
        else:
            # Sesión activa y dentro del tiempo de inactividad
            active_session.last_interaction = now()
            active_session.save()
        
    # 3️⃣ Crear una nueva sesión si no hay una activa
    if not active_session:
        active_session = ChatSession.objects.create(
            tenant=tenant,
            phone_number=phone_number,
            is_active=True,
            start_time=now(),
            last_interaction=now()
        )
        
    # 4️⃣ Guardar el mensaje en la sesión activa
    ChatMessage.objects.create(
        tenant=tenant,
        session=active_session,
        sender='client', # O 'bot' si es un mensaje del bot
        message_content=message_content,
        timestamp=now()
    )
    
    return active_session

def process_whatsapp_message(message, contact, tenant):
    message_content = message.get('text', {}).get('body')
    phone_number = contact.phone_number
    session = manage_chat_session(tenant, phone_number, message_content)
    
    return session