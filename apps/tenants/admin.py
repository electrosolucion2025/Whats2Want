import csv
import json

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpResponse

from apps.tenants.models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "nif", "phone_number", "phone_number_id", "is_active", "created_at") # ✅ Campos a mostrar
    search_fields = ("name", "nif", "phone_number", "phone_number_id")  # ✅ Búsqueda rápida
    list_filter = ("is_active", "created_at")  # ✅ Filtro por estado activo/inactivo
    ordering = ("-created_at",)  # ✅ Orden descendente (más recientes primero)
    actions = ["toggle_active_status", "export_as_csv", "export_as_json"]  # ✅ Acciones personalizadas
    
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
    
    # 📂 **Exportar Tenants a CSV**
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tenants.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "Nombre", "NIF", "Teléfono", "WhatsApp ID", "Activo", "Creado en"])

        for tenant in queryset:
            writer.writerow([
                tenant.id,
                tenant.name,
                tenant.nif,
                tenant.phone_number,
                tenant.phone_number_id,
                "Yes" if tenant.is_active else "No",
                tenant.created_at.strftime("%Y-%m-%d %H:%M"),
            ])

        return response

    export_as_csv.short_description = "📂 Exportar seleccionados a CSV"

    # 📂 **Exportar Tenants a JSON**
    def export_as_json(self, request, queryset):
        response = HttpResponse(content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="tenants.json"'
        
        tenants_data = []
        for tenant in queryset:
            tenants_data.append({
                "id": str(tenant.id),
                "name": tenant.name,
                "nif": tenant.nif,
                "phone_number": tenant.phone_number,
                "phone_number_id": tenant.phone_number_id,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        response.write(json.dumps(tenants_data, indent=4))
        return response

    export_as_json.short_description = "📂 Exportar seleccionados a JSON"
