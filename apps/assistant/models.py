import uuid

from django.db import models

from apps.chat.models import ChatSession
from apps.tenants.models import Tenant


# 📌 **Modelo de Sesiones del Asistente**
class AssistantSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, verbose_name="Tenant"
    )  # Relación con el inquilino
    session_id = models.CharField(
        max_length=100, unique=True, default=uuid.uuid4, verbose_name="Session ID"
    )  # ID único de la sesión de la IA
    chat_session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Chat Session"
    )  # Puede ser nulo si no está vinculado a una sesión de chat
    phone_number = models.CharField(max_length=20, verbose_name="Phone Number")  # Cliente
    is_active = models.BooleanField(default=True, verbose_name="Active Session")  # Estado de la sesión
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Session Start Time")  # Inicio
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="Session End Time")  # Fin
    context = models.JSONField(blank=True, null=True, verbose_name="Conversation Context")  # Contexto IA
    last_detected_language = models.CharField(max_length=5, default="es")

    def __str__(self):
        return f'Assistant Session {str(self.session_id)[:8]} ({self.phone_number})'

    @property
    def session_duration(self):
        """Calcula la duración de la sesión basada en el tiempo entre start_time y end_time."""
        if self.end_time:
            return self.end_time - self.start_time
        return None  # Si no ha finalizado, retorna None

    session_duration.fget.short_description = "Session Duration"


# 📌 **Modelo de Mensajes de la IA**
class AIMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, verbose_name="Tenant"
    )  # Relación con el inquilino
    session = models.ForeignKey(
        AssistantSession, on_delete=models.CASCADE, related_name="messages", verbose_name="Assistant Session"
    )  # Relación con la sesión IA
    role = models.CharField(
        max_length=20,
        choices=[
            ("user", "User"),
            ("assistant", "Assistant"),
            ("system", "System"),
        ],
        verbose_name="Sender Role",
    )  # Quién envió el mensaje
    content = models.TextField(verbose_name="Message Content")  # Contenido del mensaje
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")  # Fecha y hora

    def __str__(self):
        return f'{self.role.capitalize()} Message at {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}'


# 📌 **Modelo de Registro de Solicitudes a OpenAI**
class OpenAIRequestLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, verbose_name="Tenant"
    )  # Relación con el inquilino
    request_id = models.CharField(
        max_length=100, unique=True, verbose_name="Request ID"
    )  # ID único de la solicitud
    endpoint = models.CharField(max_length=100, verbose_name="API Endpoint")  # Endpoint de OpenAI
    payload = models.JSONField(verbose_name="Request Payload")  # Datos enviados
    response = models.JSONField(verbose_name="API Response")  # Respuesta de OpenAI
    status_code = models.IntegerField(verbose_name="HTTP Status Code")  # Código HTTP
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")  # Fecha y hora

    def __str__(self):
        return f'OpenAI Request {self.request_id} - {self.endpoint}'
