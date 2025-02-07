import csv
import json
from django.contrib import admin, messages
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html
from django.utils.timezone import localtime

from apps.payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_id", "tenant", "order", "amount", "currency", "status", 
        "transaction_date_formatted", "payment_method"
    )
    list_filter = ("status", "currency", "transaction_date", "tenant")
    search_fields = ("payment_id", "order__order_number", "tenant__name", "card_last_digits")
    ordering = ("-transaction_date",)
    readonly_fields = ("created_at", "updated_at", "transaction_date")
    
    change_list_template = "admin/payments/change_list.html"  # 📌 Asociar template correctamente

    fieldsets = (
        ("Payment Information", {"fields": ("payment_id", "tenant", "order", "amount", "currency", "status")}),
        ("Transaction Details", {"fields": ("payment_method", "authorization_code", "response_code", "card_last_digits")}),
        ("Refund Information", {"fields": ("refund_reason",)}),
        ("Timestamps", {"fields": ("transaction_date", "created_at", "updated_at")}),
    )

    actions = ["mark_as_completed", "mark_as_refunded", "export_as_csv", "export_as_json"]

    def transaction_date_formatted(self, obj):
        """Muestra la fecha de transacción en formato legible."""
        return localtime(obj.transaction_date).strftime("%d/%m/%Y %H:%M")
    transaction_date_formatted.short_description = "Transaction Date"
    
    def get_urls(self):
        """Agrega URL para el dashboard de pagos."""
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/", self.admin_site.admin_view(self.payment_dashboard), name="payment_dashboard"),
        ]
        return custom_urls + urls

    def payment_dashboard(self, request):
        """Vista del dashboard de pagos."""
        total_payments = Payment.objects.aggregate(total=Sum("amount"))["total"] or 0
        completed_payments = Payment.objects.filter(status="completed").count()
        pending_payments = Payment.objects.filter(status="pending").count()
        refunded_payments = Payment.objects.filter(status="refunded").count()
        payments_by_tenant = Payment.objects.values("tenant__name").annotate(total=Sum("amount"), count=Count("id"))

        context = {
            "total_payments": total_payments,
            "completed_payments": completed_payments,
            "pending_payments": pending_payments,
            "refunded_payments": refunded_payments,
            "payments_by_tenant": payments_by_tenant,
        }
        return render(request, "admin/payments/payment_dashboard.html", context)

    def changelist_view(self, request, extra_context=None):
        """Agrega el botón de acceso al Dashboard de Pagos en la lista."""
        extra_context = extra_context or {}
        extra_context["payment_dashboard_url"] = "dashboard/"
        return super().changelist_view(request, extra_context=extra_context)

    def export_as_csv(self, request, queryset):
        """Exporta pagos seleccionados a CSV."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="payments.csv"'
        writer = csv.writer(response)
        writer.writerow(["Payment ID", "Tenant", "Order", "Amount", "Currency", "Status", "Date"])

        for payment in queryset:
            writer.writerow([
                payment.payment_id,
                payment.tenant.name,
                payment.order.order_number,
                payment.amount,
                payment.currency,
                payment.status,
                localtime(payment.transaction_date).strftime("%d/%m/%Y %H:%M")
            ])

        return response

    export_as_csv.short_description = "📄 Exportar Pagos a CSV"

    def export_as_json(self, request, queryset):
        """Exporta pagos seleccionados a JSON."""
        payments_data = []
        for payment in queryset:
            payments_data.append({
                "payment_id": payment.payment_id,
                "tenant": payment.tenant.name,
                "order": payment.order.order_number,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "transaction_date": localtime(payment.transaction_date).strftime("%Y-%m-%d %H:%M:%S")
            })

        response = HttpResponse(json.dumps(payments_data, indent=4), content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="payments.json"'
        return response

    export_as_json.short_description = "📄 Exportar Pagos a JSON"
