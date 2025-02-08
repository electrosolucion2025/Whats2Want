import json
from django.contrib import admin, messages
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html
from django.http import HttpResponse

from apps.chat.models import ChatSession, ChatMessage, ConversationHistory


# 📌 **Admin de Sesiones de Chat**
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id_short", "tenant", "phone_number", "is_active", "last_interaction", "real_session_duration"
    )
    list_filter = ("is_active", "tenant", "start_time")
    search_fields = ("phone_number", "id")
    ordering = ("-last_interaction",)
    readonly_fields = ("start_time", "last_interaction", "real_session_duration")
    actions = ["end_sessions"]

    def id_short(self, obj):
        """Muestra un ID corto de la sesión para mayor legibilidad."""
        return str(obj.id)[:8]

    id_short.short_description = "Chat ID"

    def end_sessions(self, request, queryset):
        """Finaliza las sesiones de chat seleccionadas."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"✅ {count} sesión(es) finalizada(s).", messages.SUCCESS)

    end_sessions.short_description = "🚫 Finalizar Sesiones"
    
    def real_session_duration(self, obj):
        """Muestra la duración de la sesión en formato legible."""
        duration = obj.real_session_duration
        return f"{duration.seconds // 3600}h {duration.seconds % 3600 // 60}m {duration.seconds % 60}s"

    real_session_duration.short_description = "Session Duration"


# 📌 **Admin de Mensajes de Chat**
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "tenant", "sender", "short_message", "timestamp")
    list_filter = ("tenant", "sender", "timestamp")
    search_fields = ("message_content", "session__id")
    ordering = ("-timestamp",)

    def short_message(self, obj):
        """Muestra un resumen del mensaje en la lista."""
        return obj.message_content[:50] + "..." if len(obj.message_content) > 50 else obj.message_content

    short_message.short_description = "Message Preview"


# 📌 **Admin de Historial de Conversaciones**
@admin.register(ConversationHistory)
class ConversationHistoryAdmin(admin.ModelAdmin):
    list_display = ("session", "tenant", "created_at", "export_actions")
    list_filter = ("tenant", "created_at")
    ordering = ("-created_at",)
    actions = ["export_chat_history_json"]

    def export_actions(self, obj):
        """Botón para exportar el historial de chat como JSON."""
        return format_html(
            '<a class="button" style="color:white; background:#28a745; padding:3px 8px; border-radius:5px; text-decoration:none;" href="/admin/chat/conversationhistory/{}/export/">📤 Export</a>',
            obj.id
        )

    export_actions.short_description = "Export"

    def export_chat_history_json(self, request, queryset):
        """Exporta el historial de chat seleccionado en JSON."""
        chat_data = []
        for history in queryset:
            chat_data.append({
                "session_id": str(history.session.id),
                "tenant": history.tenant.name,
                "conversation": history.full_conversation,
                "created_at": history.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        response = HttpResponse(json.dumps(chat_data, indent=4), content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="chat_history.json"'
        return response

    export_chat_history_json.short_description = "📥 Exportar Chat en JSON"

