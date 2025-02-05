import uuid
import openai

from django.conf import settings
from .prompt import get_base_prompt
from apps.assistant.models import AIMessage, OpenAIRequestLog
from apps.chat.models import ChatMessage
from apps.menu.services import get_menu_data
from apps.tenants.models import TenantPrompt

openai.api_key = settings.OPENAI_API_KEY

def generate_openai_response(message, session):
    user_message = message.get('text', {}).get('body')
    base_prompt = TenantPrompt.objects.filter(tenant=session.tenant, is_active=True).first()
    
    prompt_content = base_prompt.content if base_prompt else get_base_prompt()
    
    # 📋 Obtener el menú del tenant
    menu_data = get_menu_data(session.tenant)
    
    # 🚀 Preparar el contexto inicial
    messages = [
        {"role": "system", "content": prompt_content}
    ]
    
    # 🗂️ Añadir el menú si existe
    if menu_data:
        messages.append({"role": "system", "content": f"📋 Menú actual: {menu_data}"})

    # 🗂️ Añadir historial de la sesión
    context_messages = [
        {"role": msg.role if msg.role in ['user', 'assistant', 'system'] else 'user', "content": msg.content}
        for msg in session.messages.order_by('-timestamp')[:30][::-1]
    ]
    messages += context_messages

    # 🆕 Añadir el mensaje del usuario
    messages.append({"role": "user", "content": user_message})

    # 📦 Preparar la solicitud a OpenAI
    request_id = str(uuid.uuid4())
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.3,
    }
    
    try:
        # 🚀 Llamada a la API de OpenAI
        response = openai.chat.completions.create(**payload)
        ai_response = response.choices[0].message.content
        
        # 💾 Guardar el mensaje de la IA
        ChatMessage.objects.create(
            tenant=session.tenant,
            session=session.chat_session,
            sender='bot',
            message_content=ai_response
        )
        
        AIMessage.objects.create(
            tenant=session.tenant,
            session=session,
            role='assistant',
            content=ai_response
        )
        
        # 📋 Registrar la solicitud y la respuesta
        OpenAIRequestLog.objects.create(
            tenant=session.tenant,
            request_id=request_id,
            endpoint="ChatCompletion",
            payload=payload,
            response=response.to_dict(),
            status_code=200
        )
        
        return ai_response

    except Exception as e:
        # 🚨 Registrar el error
        OpenAIRequestLog.objects.create(
            tenant=session.tenant,
            request_id=request_id,
            endpoint="ChatCompletion",
            payload=payload,
            response={"error": str(e)},
            status_code=500
        )
        return f"Error al generar respuesta: {str(e)}"
