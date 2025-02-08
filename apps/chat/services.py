from datetime import timedelta
from django.utils.timezone import now

from apps.assistant.models import AIMessage, AssistantSession
from apps.chat.models import ChatMessage, ChatSession

# TODO: Definir el tiempo de inactividad para cerrar la sesión
SESSION_TIMEOUT = timedelta(minutes=3)  # Tiempo de inactividad para cerrar la sesión


# ✅ 1️⃣ Gestión de la sesión de chat
def manage_chat_session(tenant, phone_number, message_content):
    # Verificar si existe una sesión activa para el contacto
    active_session = ChatSession.objects.filter(
        tenant=tenant,
        phone_number=phone_number,
        is_active=True
    ).first()

    # Si hay una sesión activa, verificar el tiempo de inactividad
    if active_session:
        if (now() - active_session.last_interaction) > SESSION_TIMEOUT:
            # La sesión ha superado el tiempo de inactividad
            close_chat_and_assistant_session(active_session)
            active_session = None
        else:
            # La sesión está activa y dentro del tiempo de inactividad
            active_session.last_interaction = now()
            active_session.save()

    # Crear una nueva sesión si no hay una activa
    if not active_session:
        active_session = ChatSession.objects.create(
            tenant=tenant,
            phone_number=phone_number,
            is_active=True,
            start_time=now(),
            last_interaction=now()
        )

        # 🚀 Crear una nueva AssistantSession vinculada a la ChatSession
        AssistantSession.objects.create(
            tenant=tenant,
            chat_session=active_session,
            phone_number=phone_number,
            is_active=True,
            start_time=now(),
        )

    # Guardar el mensaje del cliente en la ChatSession
    ChatMessage.objects.create(
        tenant=tenant,
        session=active_session,
        sender='client',
        message_content=message_content,
        timestamp=now()
    )

    return active_session


# ✅ 2️⃣ Procesamiento del mensaje de WhatsApp
def process_whatsapp_message(message, contact, tenant, transcribed_text=None):
    """
    Procesa el mensaje de WhatsApp para gestionar la sesión de chat y la IA.
    Si es un audio, usa `transcribed_text` como el contenido del mensaje.
    """
    # Determinar el contenido del mensaje
    if transcribed_text:  # Si es un audio transcrito, usarlo
        message_content = transcribed_text
    else:
        message_content = message.get("text", {}).get("body")

    if not message_content:
        return None  # Evita procesar mensajes vacíos o sin contenido útil

    phone_number = contact.phone_number

    # Obtener o crear la sesión de chat
    chat_session = manage_chat_session(tenant, phone_number, message_content)

    # Verificar si existe una sesión de IA asociada, si no, crearla
    assistant_session, _ = AssistantSession.objects.get_or_create(
        chat_session=chat_session,
        defaults={
            "tenant": tenant,
            "phone_number": phone_number,
            "is_active": True,
            "start_time": now(),
        },
    )

    # Guardar el mensaje del usuario en la sesión de IA
    AIMessage.objects.create(
        tenant=tenant,
        session=assistant_session,
        role="user",
        content=message_content,  # Guardamos el texto transcrito o el mensaje normal
    )

    return assistant_session

# ✅ 3️⃣ Cierre de sesiones de Chat y Asistente
def close_chat_and_assistant_session(chat_session):
    now_time = now()

    # Cerrar la ChatSession
    chat_session.is_active = False
    chat_session.end_time = now_time
    chat_session.save()

    # Cerrar la AssistantSession vinculada (si existe)
    assistant_session = AssistantSession.objects.filter(
        chat_session=chat_session,
        is_active=True
    ).first()

    if assistant_session:
        assistant_session.is_active = False
        assistant_session.end_time = now_time
        assistant_session.save()
