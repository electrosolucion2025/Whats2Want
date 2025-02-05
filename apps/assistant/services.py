import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

def generate_openai_response(message, context=None):
    user_message = message.get('text', {}).get('body')
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un camarero virtual que ayuda a los clientes a realizar pedidos."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Error al generar respuesta: {str(e)}"