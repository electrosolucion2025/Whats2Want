from django.contrib import admin
from apps.whatsapp.models import WhatsAppContact, WhatsAppMessage, MessageStatus, WebhookEvent

# 📌 **Admin de Contactos de WhatsApp**
@admin.register(WhatsAppContact)
class WhatsAppContactAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "name", "get_tenants", "last_interaction")
    list_filter = ("tenants",)  # Corrección para ManyToManyField
    search_fields = ("phone_number", "name", "wa_id")

    def get_tenants(self, obj):
        """Muestra los tenants asociados en el listado del admin."""
        return ", ".join([t.name for t in obj.tenants.all()])
    
    get_tenants.short_description = "Tenants"

# 📌 **Admin de Mensajes de WhatsApp**
@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ("message_id", "tenant", "from_number", "to_number", "message_type", "short_content", "status", "direction", "timestamp")
    list_filter = ("message_type", "status", "direction", "tenant", "timestamp")
    search_fields = ("message_id", "from_number", "to_number", "content", "tenant__name")
    ordering = ("-timestamp",)

    fieldsets = (
        ("Información del Mensaje", {"fields": ("message_id", "tenant", "from_number", "to_number", "message_type", "status", "direction", "timestamp")}),
        ("Contenido", {"fields": ("content",)}),
    )

    readonly_fields = ("message_id", "timestamp")

    def short_content(self, obj):
        """Muestra un preview corto del contenido del mensaje."""
        return obj.content[:50] + "..." if obj.content and len(obj.content) > 50 else obj.content

    short_content.short_description = "Vista Previa"

# 📌 **Admin de Estados de Mensajes**
@admin.register(MessageStatus)
class MessageStatusAdmin(admin.ModelAdmin):
    list_display = ("message", "tenant", "status", "timestamp")
    list_filter = ("status", "tenant", "timestamp")
    search_fields = ("message__message_id", "tenant__name")
    ordering = ("-timestamp",)

    fieldsets = (
        ("Estado del Mensaje", {"fields": ("message", "tenant", "status", "timestamp")}),
    )

    readonly_fields = ("timestamp",)

# 📌 **Admin de Webhook de WhatsApp**
@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "tenant", "received_at")
    search_fields = ("event_type", "tenant__name")
    list_filter = ("tenant", "event_type", "received_at")
    ordering = ("-received_at",)

    fieldsets = (
        ("Información del Evento", {"fields": ("event_type", "tenant", "received_at")}),
        ("Datos del Webhook", {"fields": ("payload",)}),
    )

    readonly_fields = ("received_at",)
