import json
import openai
import re
import uuid

from django.conf import settings
from apps.orders.services import save_order_to_db
from .prompt import get_base_prompt
from apps.assistant.models import AIMessage, OpenAIRequestLog
from apps.chat.models import ChatMessage
from apps.menu.services import get_menu_data
from apps.tenants.models import TenantPrompt

openai.api_key = settings.OPENAI_API_KEY


def remove_json_blocks(text):
    """Eliminar cualquier bloque JSON del texto, ya sea en Markdown o como parte del mensaje."""
    
    # 🏷️ Paso 1: Eliminar bloques JSON en formato Markdown ```json ... ```
    text = re.sub(r'```json.*?```', '', text, flags=re.DOTALL).strip()

    # 🏷️ Paso 2: Detectar y eliminar JSON al final del texto
    json_match = re.search(r'(\{.*"order_finalized":\s*true.*\})', text, re.DOTALL)
    
    if json_match:
        print("📦 JSON detectado y eliminado:", json_match.group(1), flush=True)
        text = text.replace(json_match.group(1), "").strip()

    return text


def generate_openai_response(message, session):
    user_message = message.get('text', {}).get('body')
    base_prompt = TenantPrompt.objects.filter(tenant=session.tenant, is_active=True).first()

    prompt_content = base_prompt.content if base_prompt else get_base_prompt()

    # 📋 Obtener el menú del tenant
    menu_data = get_menu_data(session.tenant)

    # 🚀 Preparar el contexto inicial
    messages = [{"role": "system", "content": prompt_content}]

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
        print(f"📩 Respuesta de la IA (antes de limpiar JSON): {ai_response}", flush=True)

        # ❌ Eliminar bloques JSON de la respuesta
        ai_response = remove_json_blocks(ai_response)
        print(f"📩 Respuesta de la IA (después de limpiar JSON): {ai_response}", flush=True)

        # 💾 Guardar SIEMPRE el mensaje de la IA
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

        # ✅ Verificar si hay un bloque JSON para la finalización del pedido
        if 'order_finalized' in response.choices[0].message.content:
            print("✅ Pedido finalizado detectado, procesando JSON...", flush=True)
            context_messages.append({"role": "assistant", "content": response.choices[0].message.content})  # Añadir al historial
            extract_order_json(context_messages, session)

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


def extract_order_json(context_messages, session):
    print("🚀 Extrayendo JSON del pedido...", flush=True)
    for msg in context_messages[::-1]:  # Revisar desde el final hacia atrás
        content = msg.get("content", "")

        # Eliminar posibles bloques de código Markdown (```json ... ```)
        cleaned_content = re.sub(r'```json|```', '', content).strip()

        # Verificar si el contenido tiene el JSON de finalización de pedido
        if '"order_finalized": true' in cleaned_content:
            print(f"📦 JSON encontrado: {cleaned_content}", flush=True)
            try:
                # Extraer el JSON usando expresiones regulares
                json_match = re.search(r'\{.*"order_finalized": true.*\}', cleaned_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)

                    # Convertir a diccionario
                    order_data = json.loads(json_str)

                    # Guardar el pedido
                    save_order_to_db(order_data, session)
                    print("✅ Pedido guardado en la base de datos.", flush=True)
                else:
                    print("❌ No se encontró un bloque JSON válido.", flush=True)

            except json.JSONDecodeError as e:
                print(f"❌ Error al decodificar JSON: {e}", flush=True)
            break
