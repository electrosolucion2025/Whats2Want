import uuid
import openai

from django.conf import settings

from apps.assistant.models import AIMessage, OpenAIRequestLog
from apps.chat.models import ChatMessage

openai.api_key = settings.OPENAI_API_KEY


def generate_openai_response(message, session):
    user_message = message.get('text', {}).get('body')
    
    # 🗂️ 1️⃣ Obtener el historial de la sesión
    context_messages = [
        {
            "role": 'user' if msg.role == 'client' else 'assistant',
            "content": msg.content
        }
        for msg in session.messages.all().order_by('timestamp')
    ]
    
    # 🆕 2️⃣ Agregar el nuevo mensaje del usuario
    context_messages.append({"role": "user", "content": user_message})
    
    # 📦 3️⃣ Preparar la solicitud a OpenAI
    request_id = str(uuid.uuid4())
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Eres un camarero que ayuda a los clientes a realizar pedidos."
            }
        ] + context_messages,
        "temperature": 0.3,
    }
    
    try:
        # 🚀 4️⃣ Llamada a la API de OpenAI
        response = openai.chat.completions.create(**payload)
        ai_response = response.choices[0].message.content
        
        # 💾 5️⃣ Guardar el mensaje de la IA en la base de datos
        ChatMessage.objects.create(
            tenant=session.tenant,
            session=session.chat_session,
            sender='bot',
            message_content=ai_response
        )
        
        # 💡 6️⃣ Guardar también en AIMessage para análisis futuros
        AIMessage.objects.create(
            tenant=session.tenant,
            session=session,
            role='assistant',
            content=ai_response
        )
        
        # 📋 7️⃣ Registrar la solicitud y la respuesta en OpenAIRequestLog
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
        # 🚨 Registrar el error en OpenAIRequestLog
        OpenAIRequestLog.objects.create(
            tenant=session.tenant,
            request_id=request_id,
            endpoint="ChatCompletion",
            payload=payload,
            response={"error": str(e)},
            status_code=500
        )
        return f"Error al generar respuesta: {str(e)}"