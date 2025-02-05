from django.contrib import admin
from .models import WhatsAppMessage, WebhookEvent, WhatsAppContact, MessageStatus

@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'content', 'message_type', 'timestamp')
    search_fields = ('content', 'contact__name')

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_type', 'payload', 'received_at')
    search_fields = ('event_type',)

@admin.register(WhatsAppContact)
class WhatsAppContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone_number', 'last_interaction')
    search_fields = ('name', 'phone_number')

@admin.register(MessageStatus)
class MessageStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'timestamp')
