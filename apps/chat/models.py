import uuid
from datetime import timedelta

from django.utils.timezone import now
from django.db import models

from apps.tenants.models import Tenant


# 📌 **Modelo de Sesión de Chat**
class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, verbose_name="Tenant"
    )  
    phone_number = models.CharField(
        max_length=20, verbose_name="Client Phone Number", help_text="Phone number of the client."
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Active Session", help_text="Indicates if the session is active."
    )
    start_time = models.DateTimeField(
        auto_now_add=True, verbose_name="Start Time", help_text="When the session started."
    )
    end_time = models.DateTimeField(
        blank=True, null=True, verbose_name="End Time", help_text="When the session ended."
    )
    last_interaction = models.DateTimeField(
        auto_now=True, null=True, verbose_name="Last Interaction", help_text="Timestamp of last interaction."
    )
    context_data = models.JSONField(
        blank=True, null=True, verbose_name="Context Data", help_text="Stores conversation context for AI processing."
    )

    class Meta:
        verbose_name = "Chat Session"
        verbose_name_plural = "Chat Sessions"
        ordering = ["-start_time"]

    def __str__(self):
        return f"Chat {str(self.id)[:8]} ({self.phone_number})"

    @property
    def real_session_duration(self):
        """Calcula la duración de la sesión basada en el primer mensaje y la última interacción + 15 min."""
        first_message = self.messages.order_by("timestamp").first()
        if first_message:
            inicio_real = first_message.timestamp
        else:
            inicio_real = self.start_time  # Si no hay mensajes, usar start_time como fallback

        fin_real = self.last_interaction + timedelta(minutes=15) if self.last_interaction else now()
        return fin_real - inicio_real  # Duración real de la sesión

    real_session_duration.fget.short_description = "Real Session Duration"


# 📌 **Modelo de Mensajes de Chat**
class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, verbose_name="Tenant"
    )  
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages", verbose_name="Chat Session"
    )
    sender = models.CharField(
        max_length=50,
        choices=[
            ("client", "Client"),
            ("bot", "Bot"),
            ("system", "System"),
        ],
        verbose_name="Sender",
        help_text="Indicates who sent the message."
    )
    message_content = models.TextField(
        verbose_name="Message Content", help_text="Text content of the message."
    )
    timestamp = models.DateTimeField(
        auto_now_add=True, verbose_name="Timestamp", help_text="When the message was sent."
    )

    class Meta:
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Message from {self.sender} at {self.timestamp}"


# 📌 **Modelo de Historial de Conversaciones**
class ConversationHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, verbose_name="Tenant"
    )  
    session = models.OneToOneField(
        ChatSession, on_delete=models.CASCADE, related_name="history", verbose_name="Chat Session"
    )
    full_conversation = models.JSONField(
        verbose_name="Full Conversation", help_text="Stores the full chat history in JSON format."
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Created At", help_text="When the conversation history was stored."
    )

    class Meta:
        verbose_name = "Conversation History"
        verbose_name_plural = "Conversation Histories"
        ordering = ["-created_at"]

    def __str__(self):
        return f"History for Session {self.session.id}"
