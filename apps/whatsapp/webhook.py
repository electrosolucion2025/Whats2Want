import json

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .services import process_webhook_event


@method_decorator(csrf_exempt, name='dispatch')  # 👈 Esto desactiva la verificación CSRF
class WhatsAppWebhookView(View):
   def get(self, request):
      """Verificación del Webhook de Meta"""
      verify_token = 'R0m1n4'
      mode = request.GET.get('hub.mode')
      token = request.GET.get('hub.verify_token')
      challenge = request.GET.get('hub.challenge')

      if mode == 'subscribe' and token == verify_token:
         return HttpResponse(challenge, status=200)

      else:
         return HttpResponse('Verificación fallida', status=403)

   def post(self, request):
      """Recibir mensajes de WhatsApp"""
      try:
         data = json.loads(request.body)
         process_webhook_event(data)

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