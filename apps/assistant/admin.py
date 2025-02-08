import json

from django.contrib import admin
from django.db.models import Count, Avg
from django.http import HttpResponse
from django.urls import path, reverse
from django.shortcuts import render

from apps.assistant.models import AssistantSession, AIMessage, OpenAIRequestLog

change_list_template = "admin/change_list.html"

# 📌 **Admin de AssistantSession**
@admin.register(AssistantSession)
class AssistantSessionAdmin(admin.ModelAdmin):
    list_display = ("session_id", "tenant", "phone_number", "is_active", "start_time", "end_time", "session_duration_formatted")
    list_filter = ("is_active", "tenant", "start_time")
    search_fields = ("session_id", "phone_number", "tenant__name")
    ordering = ("-start_time",)

    fieldsets = (
        ("Session Info", {"fields": ("session_id", "tenant", "phone_number", "chat_session")}),
        ("Status", {"fields": ("is_active", "start_time", "end_time")}),
        ("Context Data", {"fields": ("context",)}),
    )

    readonly_fields = ("session_id", "start_time", "end_time")

    def session_duration_formatted(self, obj):
        """Calcula la duración de la sesión para mostrar en la lista."""
        if obj.end_time:
            duration = obj.end_time - obj.start_time
            return f"{duration.total_seconds() // 60:.0f} min"
        return "Active"
    
    session_duration_formatted.short_description = "Session Duration"

# 📌 **Admin de AIMessage**
@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ("tenant", "session", "role", "short_content", "timestamp")
    list_filter = ("role", "tenant", "timestamp")
    search_fields = ("session__session_id", "content", "tenant__name")
    ordering = ("-timestamp",)

    fieldsets = (
        ("Message Details", {"fields": ("tenant", "session", "role", "timestamp")}),
        ("Content", {"fields": ("content",)}),
    )

    readonly_fields = ("timestamp",)

    def short_content(self, obj):
        """Muestra un preview corto del contenido del mensaje."""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    short_content.short_description = "Message Preview"


# 📌 **Admin de OpenAIRequestLog**
@admin.register(OpenAIRequestLog)
class OpenAIRequestLogAdmin(admin.ModelAdmin):
    list_display = ("request_id", "tenant", "endpoint", "status_code", "timestamp")
    list_filter = ("status_code", "endpoint", "tenant", "timestamp")
    search_fields = ("request_id", "endpoint", "tenant__name")
    ordering = ("-timestamp",)

    fieldsets = (
        ("Request Details", {"fields": ("request_id", "tenant", "endpoint", "status_code", "timestamp")}),
        ("Request & Response Data", {"fields": ("payload", "response")}),
    )

    readonly_fields = ("timestamp",)

    def export_requests_as_json(self, request, queryset):
        """Exporta solicitudes a OpenAI en formato JSON."""
        data = [
            {
                "request_id": req.request_id,
                "tenant": req.tenant.name,
                "endpoint": req.endpoint,
                "status_code": req.status_code,
                "timestamp": req.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "payload": req.payload,
                "response": req.response,
            }
            for req in queryset
        ]
        response = HttpResponse(json.dumps(data, indent=4), content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="openai_requests.json"'
        return response

    export_requests_as_json.short_description = "📄 Export OpenAI Requests as JSON"
