import uuid

from django.db import models

TIMEZONE_CHOICES = [
    ("Europe/London", "🇬🇧 Reino Unido - Londres"),
    ("Europe/Madrid", "🇪🇸 España - Madrid"),
    ("Europe/Paris", "🇫🇷 Francia - París"),
    ("Europe/Berlin", "🇩🇪 Alemania - Berlín"),
    ("Europe/Rome", "🇮🇹 Italia - Roma"),
    ("Europe/Amsterdam", "🇳🇱 Países Bajos - Ámsterdam"),
    ("Europe/Brussels", "🇧🇪 Bélgica - Bruselas"),
    ("Europe/Lisbon", "🇵🇹 Portugal - Lisboa"),
    ("Europe/Zurich", "🇨🇭 Suiza - Zúrich"),
    ("Europe/Vienna", "🇦🇹 Austria - Viena"),
    ("Europe/Stockholm", "🇸🇪 Suecia - Estocolmo"),
    ("Europe/Copenhagen", "🇩🇰 Dinamarca - Copenhague"),
    ("Europe/Oslo", "🇳🇴 Noruega - Oslo"),
    ("Europe/Helsinki", "🇫🇮 Finlandia - Helsinki"),
    ("Europe/Athens", "🇬🇷 Grecia - Atenas"),
    ("Europe/Dublin", "🇮🇪 Irlanda - Dublín"),
    ("Europe/Prague", "🇨🇿 República Checa - Praga"),
    ("Europe/Warsaw", "🇵🇱 Polonia - Varsovia"),
    ("Europe/Budapest", "🇭🇺 Hungría - Budapest"),
    ("Europe/Sofia", "🇧🇬 Bulgaria - Sofía"),
    ("Europe/Bucharest", "🇷🇴 Rumanía - Bucarest"),
    ("Europe/Istanbul", "🇹🇷 Turquía - Estambul"),
    ("Europe/Moscow", "🇷🇺 Rusia - Moscú"),
    ("Europe/Kiev", "🇺🇦 Ucrania - Kiev"),
]

CURRENCY_CHOICES = [
    ("EUR", "💶 Euro (€)"),
    ("USD", "💵 Dólar estadounidense ($)"),
    ("GBP", "💷 Libra esterlina (£)"),
    ("CHF", "🇨🇭 Franco suizo (CHF)"),
    ("PLN", "🇵🇱 Złoty polaco (zł)"),
    ("SEK", "🇸🇪 Corona sueca (kr)"),
    ("NOK", "🇳🇴 Corona noruega (kr)"),
    ("DKK", "🇩🇰 Corona danesa (kr)"),
    ("RUB", "🇷🇺 Rublo ruso (₽)"),
    ("TRY", "🇹🇷 Lira turca (₺)"),
    ("RON", "🇷🇴 Leu rumano (lei)"),
    ("CZK", "🇨🇿 Corona checa (Kč)"),
    ("HUF", "🇭🇺 Forinto húngaro (Ft)"),
    ("UAH", "🇺🇦 Grivna ucraniana (₴)"),
    ("CAD", "🇨🇦 Dólar canadiense (C$)"),
    ("AUD", "🇦🇺 Dólar australiano (A$)"),
    ("MXN", "🇲🇽 Peso mexicano (MX$)"),
    ("BRL", "🇧🇷 Real brasileño (R$)"),
    ("ARS", "🇦🇷 Peso argentino (AR$)"),
    ("CLP", "🇨🇱 Peso chileno (CLP$)"),
]

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Company Name")  # ✅ Required
    owner_name = models.CharField(max_length=100, verbose_name="Owner Name")  # ✅ Required
    phone_number = models.CharField(max_length=20, verbose_name="Contact Phone")  # ✅ Required
    phone_number_id = models.CharField(max_length=50, verbose_name="WhatsApp Business ID")  # ✅ Required
    whatsapp_access_token = models.CharField(max_length=255, verbose_name="WhatsApp Access Token")  # ✅ Required
    email = models.EmailField(blank=True, null=True, verbose_name="Email Address")  # 🟡 Optional
    address = models.TextField(blank=True, null=True, verbose_name="Physical Address")  # 🟡 Optional
    nif = models.CharField(max_length=20, verbose_name="Tax Identification Number (NIF)")  # ✅ Required
    timezone = models.CharField(
        max_length=50, 
        choices=TIMEZONE_CHOICES, 
        default="Europe/Madrid",
        verbose_name="Time Zone"
    )  # 🟡 Optional, but with predefined values
    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default="EUR",
        verbose_name="Currency"
    )  # 🟡 Optional, but with predefined values
    is_active = models.BooleanField(default=True, verbose_name="Active?")  # 🟡 Optional
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation Date")  # 🟢 Auto
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")  # 🟢 Auto

    def __str__(self):
        return self.name

class TenantPrompt(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False, 
        verbose_name="Unique ID"
    )
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name="prompts",
        verbose_name="Associated Tenant"
    )
    name = models.CharField(
        max_length=100, 
        default="Main Prompt",
        verbose_name="Prompt Name"
    )  # ✅ Obligatorio
    content = models.TextField(
        verbose_name="Prompt Content"
    )  # ✅ Obligatorio
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Is Active?"
    )  # ✅ Obligatorio

    def __str__(self):
        return f"{self.tenant.name} - {self.name} {'(Active)' if self.is_active else '(Inactive)'}"
