import csv
import json

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.db.models import Sum, Max
from django.utils.timezone import now, timedelta

from apps.tenants.models import Tenant, TenantPrompt
from apps.orders.models import Order
from apps.whatsapp.models import WhatsAppContact

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "nif", "phone_number", "phone_number_id", "is_active")
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
        
        # Validar duplicados
        if not change:  # Solo al crear un nuevo Tenant
            if Tenant.objects.filter(nif=obj.nif).exists():
                raise ValidationError({"nif": "Ya existe un Tenant con este NIF."})
            
            if Tenant.objects.filter(phone_number=obj.phone_number).exists():
                raise ValidationError({"phone_number": "Ya existe un Tenant con este número de teléfono."})

            if Tenant.objects.filter(phone_number_id=obj.phone_number_id).exists():
                raise ValidationError({"phone_number_id": "Ya existe un Tenant con este ID de WhatsApp."})

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
    
    # 📦 Total de pedidos realizados
    def total_orders(self, obj):
        return Order.objects.filter(tenant=obj).count()
    total_orders.short_description = "Pedidos Totales"

    # 👥 Clientes únicos que han hecho al menos un pedido
    def total_customers(self, obj):
        return Order.objects.filter(tenant=obj).values("phone_number").distinct().count()
    total_customers.short_description = "Clientes que han comprado"

    # 📲 Contactos únicos que han interactuado con el bot (compradores o no)
    def total_contacts(self, obj):
        return WhatsAppContact.objects.filter(tenant=obj).count()
    total_contacts.short_description = "Usuarios que han chateado"

    # 📅 Última fecha en la que se registró un pedido
    def last_order_date(self, obj):
        last_order = Order.objects.filter(tenant=obj).aggregate(last_date=Max("created_at"))
        if last_order["last_date"]:
            return last_order["last_date"].strftime("%d/%m/%Y %H:%M")
        return "Sin pedidos"
    last_order_date.short_description = "Última actividad"

    # 💰 Ingresos en las últimas 24 horas
    def total_revenue_last_24h(self, obj):
        last_24h = now() - timedelta(hours=24)
        revenue = Order.objects.filter(tenant=obj, created_at__gte=last_24h, payment_status="PAID").aggregate(total=Sum("total_price"))
        return f"{revenue['total']:.2f} €" if revenue["total"] else "0.00 €"
    total_revenue_last_24h.short_description = "Ingresos (24h)"

    # 💵 Promedio de ingresos por pedido pagado
    def average_revenue_per_order(self, obj):
        total_orders = Order.objects.filter(tenant=obj, payment_status="PAID").count()
        total_revenue = Order.objects.filter(tenant=obj, payment_status="PAID").aggregate(total=Sum("total_price"))["total"]
        if total_orders > 0 and total_revenue:
            return f"{(total_revenue / total_orders):.2f} €"
        return "0.00 €"
    average_revenue_per_order.short_description = "Ingreso Medio/Pedido"
    
     # 🔹 Mostrar en la vista de detalle
    fieldsets = (
        ("Información Básica", {"fields": ("name", "owner_name", "phone_number", "phone_number_id", "whatsapp_access_token")}),
        ("Detalles de Negocio", {"fields": ("email", "address", "nif", "timezone", "currency")}),
        ("Estado", {"fields": ("is_active",)}),
        ("Más Información", {
            "fields": (
                "total_orders",
                "total_customers",
                "total_contacts",
                "last_order_date",
                "total_revenue_last_24h",
                "average_revenue_per_order"
            ),
       }),
    )

    readonly_fields = ("total_orders", "total_customers", "total_contacts", "last_order_date", "total_revenue_last_24h", "average_revenue_per_order")
    
@admin.register(TenantPrompt)
class TenantPromptAdmin(admin.ModelAdmin):
    list_display = ("tenant", "name", "is_active")  # ✅ Muestra el Tenant, nombre del prompt y estado
    list_filter = ("is_active", "tenant")  # ✅ Filtro por estado y tenant
    search_fields = ("tenant__name", "name")  # ✅ Búsqueda rápida por nombre del Tenant y del Prompt
    ordering = ("tenant", "name")  # ✅ Orden alfabético por Tenant y luego por Prompt
    actions = ["toggle_prompt_status"]  # ✅ Permite activar/desactivar desde la lista

    fieldsets = (
        ("Información General", {"fields": ("tenant", "name", "is_active")}),
        ("Contenido del Prompt", {"fields": ("content",)}),
    )

    def save_model(self, request, obj, form, change):
        """
        Validación: solo un `TenantPrompt` puede estar activo por Tenant.
        """
        if obj.is_active:
            TenantPrompt.objects.filter(tenant=obj.tenant).update(is_active=False)
        
        super().save_model(request, obj, form, change)

    def toggle_prompt_status(self, request, queryset):
        """
        Activa o desactiva los prompts seleccionados.
        """
        for prompt in queryset:
            prompt.is_active = not prompt.is_active
            prompt.save()
        self.message_user(request, "Estado del Prompt actualizado.")

    toggle_prompt_status.short_description = "✅ Activar/Desactivar Prompt(s)"