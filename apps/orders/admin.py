from django.contrib import admin
from django.utils.html import format_html

from apps.orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):  # 📝 Usa una tabla dentro del admin de Order
    model = OrderItem
    extra = 0  # No agrega líneas vacías por defecto
    readonly_fields = ("final_price",)  # El precio final se calcula automáticamente
    fields = (
        "product",
        "quantity",
        "price",
        "extras",
        "exclusions",
        "special_instructions",
        "final_price",
        "preparation_status"
    ) # 📌 Campos editables

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "tenant", "phone_number", "status", "payment_status", 
        "delivery_type", "table_number", "total_items", 
        "final_total", "formatted_items", "created_at"
    )  # ✅ Mostramos toda la info relevante
    search_fields = ("order_number", "phone_number", "tenant__name")
    list_filter = ("status", "payment_status", "delivery_type", "created_at")
    ordering = ("-created_at",)

    fieldsets = (
        ("📌 Order Details", {"fields": ("tenant", "order_number", "phone_number", "chat_session")}),
        ("📦 Order Items & Status", {"fields": ("status", "total_items", "total_price", "discount", "tax_amount", "final_total")}),
        ("💳 Payment & Printer", {"fields": ("payment_status", "payment_reference", "printer_status")}),
        ("🛵 Delivery Info", {"fields": ("delivery_type", "table_number", "is_scheduled", "scheduled_time")}),
        ("📅 Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    readonly_fields = ("created_at", "updated_at", "total_items", "total_price", "discount", "tax_amount", "final_total")

    inlines = [OrderItemInline]  # ✅ Ahora los `OrderItem` aparecen dentro del pedido

    def formatted_items(self, obj):
        """
        Muestra los productos del pedido en una segunda línea en la lista de pedidos.
        """
        if not obj.items.exists():
            return "—"

        return format_html(
            "<ul style='padding-left: 15px; margin: 5px 0; list-style-type:none;'>"
            + "".join(f"<li>🍽️ {item.quantity}x {item.product.name}</li>" for item in obj.items.all())
            + "</ul>"
        )

    formatted_items.short_description = "Productos"

    def total_items(self, obj):
        """Devuelve la cantidad total de productos en el pedido."""
        return obj.get_total_items()
    total_items.short_description = "Total Items"

    def final_total(self, obj):
        """Devuelve el total final después de impuestos y descuentos."""
        return f"{obj.get_final_total():.2f}€"
    final_total.short_description = "Final Total (€)"

    actions = ["mark_as_completed", "mark_as_cancelled"]

    def mark_as_completed(self, request, queryset):
        """Acción para marcar pedidos como completados."""
        queryset.update(status="COMPLETED")
        self.message_user(request, "Selected orders have been marked as completed.")
    mark_as_completed.short_description = "✅ Mark as Completed"

    def mark_as_cancelled(self, request, queryset):
        """Acción para marcar pedidos como cancelados."""
        queryset.update(status="CANCELLED")
        self.message_user(request, "Selected orders have been marked as cancelled.")
    mark_as_cancelled.short_description = "❌ Mark as Cancelled"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "formatted_extras", "formatted_exclusions", "preparation_status")  # 📌 Agregamos columnas personalizadas
    search_fields = ("order__order_number", "product__name")  
    list_filter = ("preparation_status",)  
    ordering = ("-order__created_at",)  
    list_editable = ("preparation_status",)  
    readonly_fields = ("final_price", "served_at")  

    def formatted_extras(self, obj):
        """
        Muestra los extras de manera formateada en la lista.
        """
        if not obj.extras:
            return "—"
        return format_html(
            "<ul style='padding-left: 15px; margin: 0;'>"
            + "".join(f"<li>{extra['name']} (+{extra['price']}€)</li>" for extra in obj.extras)
            + "</ul>"
        )

    formatted_extras.short_description = "Extras"

    def formatted_exclusions(self, obj):
        """
        Muestra las exclusiones de manera formateada en la lista.
        """
        if not obj.exclusions:
            return "—"

        # Verificar si obj.exclusions es una lista, si no, convertirlo a lista
        exclusions = obj.exclusions if isinstance(obj.exclusions, list) else [obj.exclusions]

        return format_html(
            "<ul style='padding-left: 15px; margin: 0;'>"
            + "".join(f"<li>❌ {exclusion}</li>" for exclusion in exclusions)
            + "</ul>"
        )

    formatted_exclusions.short_description = "Exclusiones"
    