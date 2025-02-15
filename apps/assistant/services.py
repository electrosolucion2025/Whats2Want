# Python standard library imports
import json
import re
import uuid

# Third party imports
import openai
from django.conf import settings

# Local application imports
from .prompt import get_base_prompt
from apps.assistant.models import AIMessage, OpenAIRequestLog
from apps.chat.models import ChatMessage
from apps.menu.services import get_menu_data
from apps.orders.services import save_order_to_db
from apps.tenants.models import TenantPrompt
from apps.whatsapp.utils import (
    send_policy_interactive_message,
)


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

def detect_language_openai(text):
    """Detecta el idioma de un mensaje usando OpenAI"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Detecta el idioma de este texto y responde solo con el código de idioma ISO 639-1. Si unicamente te escriben un valor numerico (1 o 4), el idioma sigue siendo español:"},
                      {"role": "user", "content": text}]
        )
        detected_lang = response.choices[0].message.content.strip()
        return detected_lang if len(detected_lang) == 2 else "es"  # Si falla, asumimos español
    except Exception as e:
        print(f"⚠️ Error detectando idioma: {e}", flush=True)
        return "es"  # Fallback a español en caso de error
    
def translate_text_openai(text, target_language):
    """Traduce un texto al idioma deseado usando OpenAI."""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": f"Traduce este texto al {target_language}, si unicamente te escriben un valor numerico (1 o 4), el idioma sigue siendo español:"},
                      {"role": "user", "content": text}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Error traduciendo texto: {e}", flush=True)
        return text  # Si hay error, devolver el texto original

def protect_product_names(text, product_list):
    """
    Sustituye los nombres de los productos en el texto por marcadores temporales
    para evitar que se traduzcan.
    """
    protected_names = {}
    for idx, product in enumerate(product_list):
        placeholder = f"##PRODUCT{idx}##"
        protected_names[placeholder] = product
        text = re.sub(rf'\b{re.escape(product)}\b', placeholder, text, flags=re.IGNORECASE)
    
    return text, protected_names

def restore_product_names(text, protected_names):
    """
    Restaura los nombres originales de los productos en el texto después de la traducción.
    """
    for placeholder, product in protected_names.items():
        text = text.replace(placeholder, product)
    return text

def generate_openai_response(message, session, contact, transcribed_text=None):
    """Genera una respuesta de OpenAI asegurando que sea en el idioma del usuario"""

    # 📌 Obtener el mensaje del usuario
    user_message = transcribed_text if transcribed_text else message.get('text', {}).get('body')

    if not user_message:
        return "No se recibió ningún contenido válido para procesar."
    
    if not contact.policy_accepted:
        send_policy_interactive_message(contact.phone_number, session.tenant)
        return "📜 Antes de continuar, por favor acepta nuestra política de privacidad en el mensaje interactivo enviado. Gracias."

    # 🔍 Detectar idioma antes de continuar
    detected_language = detect_language_openai(user_message)
    print(f"🔍 Idioma detectado: {detected_language}", flush=True)

    # 📍 Verificar si el idioma cambió en la sesión
    if session.last_detected_language != detected_language:
        print(f"🌍 Cambio de idioma detectado: {session.last_detected_language} → {detected_language}", flush=True)
        session.last_detected_language = detected_language
        session.save()

    # 📋 Obtener el prompt base del tenant
    base_prompt = TenantPrompt.objects.filter(tenant=session.tenant, is_active=True).first()
    prompt_content = base_prompt.content if base_prompt else get_base_prompt()
    
    if contact.first_buy:
        print("🎁 Este es el primer pedido del usuario. Insertando promoción en el prompt.", flush=True)

        promo_message = "**PROMOCIÓN ACTIVA**: ¡Este cliente tiene un café gratis por su primera compra a elegir entre café espresso, café con leche y café cortado, unicamente si ha elegido algo más aparte del café! ☕🎉 Si ha pedido un café, dile que es de regalo y pon su 'unit_price': 0 en el JSON, no modifiques otro valor. Para que esta promoción sea válida, el cliente debe haber pedido al menos un producto aparte del café. Si el cliente no ha pedido un café, antes de terminar el pedido, recuérdale la promoción y dile que puede elegir un café gratis si compra al menos un producto adicional."

        # 🔹 Reemplazar marcador en el prompt
        if "[Insertar promo si hay disponible]" in prompt_content:
            prompt_content = prompt_content.replace("[Insertar promo si hay disponible]", promo_message)
        else:
            print("⚠️ No se encontró el marcador de promoción en el prompt.", flush=True)

    # 📋 Obtener el menú del tenant
    menu_data = get_menu_data(session.tenant)

    # 🛑 Extraer nombres de productos para protegerlos antes de traducir
    product_names = []
    if menu_data:
        for category in menu_data.get("menu", []):
            for product in category.get("items", []):
                product_names.append(product["name"])

    # 🚀 Preparar el contexto inicial
    messages = [{"role": "system", "content": prompt_content}]

    # 🗂️ Añadir el menú en español (sin traducción aún)
    if menu_data:
        messages.append({"role": "system", "content": f"📋 Menú en español: {menu_data}"})

    # 🗂️ Añadir historial de la sesión
    context_messages = [
        {"role": msg.role if msg.role in ['user', 'assistant', 'system'] else 'user', "content": msg.content}
        for msg in session.messages.order_by('-timestamp')[:30][::-1]
    ]
    messages += context_messages

    # 🆕 Añadir el mensaje del usuario con etiqueta de idioma
    messages.append({"role": "user", "content": f"[Idioma detectado: {detected_language}] {user_message}"})

    # 📦 Preparar la solicitud a OpenAI
    request_id = str(uuid.uuid4())
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.4,
    }

    try:
        # 🚀 Llamada a OpenAI
        response = openai.chat.completions.create(**payload)
        ai_response = response.choices[0].message.content
        print(f"📩 Respuesta de la IA (antes de limpiar JSON): {ai_response}", flush=True)
        
        # ❌ Eliminar bloques JSON de la respuesta
        ai_response = remove_json_blocks(ai_response)
        
        # 🔍 Detectar el idioma de la respuesta de OpenAI
        response_language = detect_language_openai(ai_response).lower()
        print(f"🔍 Idioma detectado en respuesta de OpenAI: {response_language}", flush=True)

        # 🔄 Si la respuesta está en otro idioma, proteger nombres de productos antes de traducir
        if response_language != detected_language:
            print(f"🔄 Traduciendo respuesta de {response_language} a {detected_language}...", flush=True)

            # 🚀 Proteger nombres de productos
            ai_response_protected, protected_names = protect_product_names(ai_response, product_names)

            # 🔄 Traducir el texto con nombres protegidos
            translated_response = translate_text_openai(ai_response_protected, target_language=detected_language)

            # 🔙 Restaurar nombres de productos después de traducir
            ai_response = restore_product_names(translated_response, protected_names)

        print(f"📩 Respuesta de la IA (final después de traducir y restaurar nombres): {ai_response}", flush=True)

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
