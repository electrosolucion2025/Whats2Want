from django.urls import path
from .webhook import WhatsAppWebhookView

urlpatterns = [
    path('webhook/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
]
