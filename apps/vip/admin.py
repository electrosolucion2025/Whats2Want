from django.contrib import admin
from .models import VIPAccess

@admin.register(VIPAccess)
class VIPAccessAdmin(admin.ModelAdmin):
    list_display = ("contact", "tenant", "permissions", "created_at")  # Columnas en la lista
    list_filter = ("tenant", "permissions")  # Filtros para buscar rápido
    search_fields = ("contact__phone_number", "tenant__name")  # Buscar por número y negocio
    list_editable = ("permissions",)  # Permitir edición rápida de permisos
    ordering = ("-created_at",)  # Mostrar VIPs más recientes primero
    readonly_fields = ("created_at", "updated_at")  # No permitir editar fechas

    fieldsets = (
        ("Información General", {"fields": ("contact", "tenant")}),
        ("Privilegios", {"fields": ("permissions",)}),
        ("Metadatos", {"fields": ("created_at", "updated_at")}),
    )

    def has_delete_permission(self, request, obj=None):
        """Evita que se borren VIPs accidentalmente desde el admin"""
        return True  # Se puede cambiar a `True` si deseas permitirlo
