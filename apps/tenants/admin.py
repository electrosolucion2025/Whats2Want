from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from apps.tenants.models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "nif", "phone_number", "phone_number_id", "is_active", "created_at")  # ✅ Agregamos "is_active" y "action_buttons"
    search_fields = ("name", "nif", "phone_number", "phone_number_id")  # ✅ Búsqueda rápida
    list_filter = ("is_active", "created_at")  # ✅ Filtro por estado activo/inactivo
    ordering = ("-created_at",)  # ✅ Orden descendente (más recientes primero)
    actions = ["toggle_active_status"]  # ✅ Acciones personalizadas
    
    def save_model(self, request, obj, form, change):
        """
        Verifica que los campos obligatorios no estén vacíos antes de guardar el Tenant.
        """
        required_fields = ["name", "owner_name", "phone_number", "phone_number_id", "whatsapp_access_token", "nif"]
        for field in required_fields:
            if not getattr(obj, field, None):  # Si está vacío o es None
                raise ValidationError({field: f"El campo {field} es obligatorio."})
        
        super().save_model(request, obj, form, change)
    
    def toggle_active_status(self, request, queryset):
        """
        Activa o desactiva los Tenants seleccionados desde la lista de administración.
        """
        for tenant in queryset:
            tenant.is_active = not tenant.is_active  # Cambia el estado actual
            tenant.save()
        self.message_user(request, "Estado actualizado correctamente.")
    
    toggle_active_status.short_description = "✅ Activar/Desactivar Tenant(s)"
