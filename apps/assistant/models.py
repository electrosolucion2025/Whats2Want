import uuid

from django.db import models
from apps.tenants.models import Tenant

# Modelo de Sesiones del Asistente
class AssistantSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    session_id = models.CharField(max_length=100, unique=True)  # ID único de la sesión de la IA
    phone_number = models.CharField(max_length=20)  # Número del cliente que interactúa con la IA
    is_active = models.BooleanField(default=True)  # Estado de la sesión
    start_time = models.DateTimeField(auto_now_add=True)  # Inicio de la sesión
    end_time = models.DateTimeField(blank=True, null=True)  # Fin de la sesión
    context = models.JSONField(blank=True, null=True)  # Contexto de la conversación para OpenAI

    def __str__(self):
        return f'Assistant Session {self.session_id}'

# Modelo de Mensajes de la IA
class AIMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    session = models.ForeignKey(AssistantSession, on_delete=models.CASCADE, related_name='messages')  # Relación con la sesión de la IA
    role = models.CharField(max_length=20, choices=[
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ])  # Quién envió el mensaje
    content = models.TextField()  # Contenido del mensaje
    timestamp = models.DateTimeField(auto_now_add=True)  # Fecha y hora del mensaje

    def __str__(self):
        return f'{self.role.capitalize()} Message at {self.timestamp}'

# Modelo de Registro de Solicitudes a OpenAI
class OpenAIRequestLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    request_id = models.CharField(max_length=100, unique=True)  # ID único de la solicitud
    endpoint = models.CharField(max_length=100)  # Endpoint de OpenAI utilizado
    payload = models.JSONField()  # Datos enviados en la solicitud
    response = models.JSONField()  # Respuesta de OpenAI
    status_code = models.IntegerField()  # Código de estado HTTP de la respuesta
    timestamp = models.DateTimeField(auto_now_add=True)  # Fecha y hora de la solicitud

    def __str__(self):
        return f'OpenAI Request {self.request_id}'
