from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from apps.assistant.models import AssistantSession

@staff_member_required
def assistant_dashboard(request):
    """Genera estadísticas sobre el uso del asistente de IA."""

    # 🔹 Total de sesiones
    total_sessions = AssistantSession.objects.count()

    # 🔹 Sesiones activas
    active_sessions = AssistantSession.objects.filter(is_active=True).count()

    # 🔹 Calcular la duración promedio de sesiones (excluyendo las activas sin fin)
    avg_duration = (
        AssistantSession.objects.exclude(end_time=None)
        .annotate(duration=ExpressionWrapper(F("end_time") - F("start_time"), output_field=fields.DurationField()))
        .aggregate(avg_duration=Avg("duration"))["avg_duration"]
    )
    avg_duration_minutes = round(avg_duration.total_seconds() / 60) if avg_duration else 0

    # 🔹 Distribución de sesiones por Tenant
    sessions_by_tenant = AssistantSession.objects.values("tenant__name").annotate(count=Count("id"))

    context = {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "avg_duration": avg_duration_minutes,
        "sessions_by_tenant": sessions_by_tenant,
    }

    return render(request, "admin/assistant_dashboard.html", context)
