import json

from django.http import HttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.timezone import make_aware
from datetime import datetime

from apps.whatsapp.models import WebhookEvent, WhatsAppContact, WhatsAppMessage
from apps.tenants.models import Tenant


@method_decorator(csrf_exempt, name='dispatch')  # 👈 Esto desactiva la verificación CSRF
class WhatsAppWebhookView(View):
   def get(self, request, *args, **kwargs):
      """Verificación del Webhook de Meta"""
      verify_token = 'R0m1n4'
      mode = request.GET.get('hub.mode')
      token = request.GET.get('hub.verify_token')
      challenge = request.GET.get('hub.challenge')

      if mode == 'subscribe' and token == verify_token:
         return HttpResponse(challenge, status=200)

      else:
         return HttpResponse('Verificación fallida', status=403)

   def post(self, request, *args, **kwargs):
      """Recibir mensajes de WhatsApp"""
      try:
         data = json.loads(request.body)
         
         # 1️⃣ Obtener el número de teléfono receptor del webhook
         phone_number = data.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('metadata', {}).get('display_phone_number')
         
         # 2️⃣ Obtener el Tenant asociado a ese número
         tenant = Tenant.objects.get(phone_number=phone_number)
         
         if not tenant:
            return JsonResponse({'error': 'Tenant no encontrado para el número de teléfono'}, status=404)
         
         #3️⃣ Guardar el evento del webhook
         webhook_event = WebhookEvent.objects.create(
            event_type=data.get('object'),
            payload=data,
            tenant=tenant
         )
         
         # 4️⃣ Procesar cada cambio recibido
         for entry in data.get('entry', []):
            changes = entry.get('changes', [])
            for change in changes:
               value = change.get('value', {})
               messages = value.get('messages', [])
               contacts = value.get('contacts', [])
               
               # 5️⃣ Guardar o actualizar contacto
               for contact in contacts:
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
                     
                  # 6️⃣ Guardar los mensajes recibidos
                  for message in messages:
                     message_id = message.get('id')
                     message_from = message.get('from')
                     message_type = message.get('type')
                     timestamp = message.get('timestamp')
                     content = message.get('text', {}).get('body')
                     
                     # Convertir el timestamp a un objeto datetime
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
                     
         return JsonResponse({'status': 'received'}, status=200)

      except json.JSONDecodeError:
         return JsonResponse({'error': 'Invalid JSON'}, status=400)

"""
{
   "object":"whatsapp_business_account",
   "entry":[
      {
         "id":"0",
         "changes":[
            {
               "field":"messages",
               "value":{
                  "messaging_product":"whatsapp",
                  "metadata":{
                     "display_phone_number":"16505551111",
                     "phone_number_id":"123456123"
                  },
                  "contacts":[
                     {
                        "profile":{
                           "name":"test user name"
                        },
                        "wa_id":"16315551181"
                     }
                  ],
                  "messages":[
                     {
                        "from":"16315551181",
                        "id":"ABGGFlA5Fpa",
                        "timestamp":"1504902988",
                        "type":"text",
                        "text":{
                           "body":"this is a text message"
                        }
                     }
                  ]
               }
            }
         ]
      }
   ]
}
"""