import uuid

from django.db import models
from apps.tenants.models import Tenant

# Modelo de Sesión de Chat
class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    phone_number = models.CharField(max_length=20)  # Número de teléfono del cliente
    is_active = models.BooleanField(default=True)  # Estado de la sesión (activa o finalizada)
    start_time = models.DateTimeField(auto_now_add=True)  # Inicio de la sesión
    end_time = models.DateTimeField(blank=True, null=True)  # Fin de la sesión
    last_interaction = models.DateTimeField(auto_now=True, null=True)  # Última interacción
    context_data = models.JSONField(blank=True, null=True)  # Contexto de la conversación (para ChatGPT)

    def __str__(self):
        return f'Session {self.session_id} - {self.phone_number}'
    
    @property
    def session_duration(self):
        """Calcula la duración de la sesión"""
        if self.last_interaction:
            return self.last_interaction - self.start_time
        return timedelta(0) # Duración de 0 si no hay interacciones

# Modelo de Mensajes de Chat
class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')  # Relación con la sesión de chat
    sender = models.CharField(max_length=50, choices=[
        ('client', 'Client'),
        ('bot', 'Bot'),
        ('system', 'System'),
    ])  # Quién envió el mensaje
    message_content = models.TextField()  # Contenido del mensaje
    timestamp = models.DateTimeField(auto_now_add=True)  # Fecha y hora del mensaje

    def __str__(self):
        return f'Message from {self.sender} at {self.timestamp}'

# Modelo de Historial de Conversaciones
class ConversationHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Relación con el inquilino
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='history')  # Relación con la sesión de chat
    full_conversation = models.JSONField()  # Conversación completa (formato JSON)
    created_at = models.DateTimeField(auto_now_add=True)  # Fecha de creación del historial

    def __str__(self):
        return f'History for Session {self.session.session_id}'
    