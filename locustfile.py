from locust import HttpUser, task, between
import random

class WhatsAppUser(HttpUser):
    wait_time = between(3, 5)  # Intervalo de espera entre mensajes

    @task
    def send_whatsapp_message(self):
        phone_number = "34607227417"  # Reemplaza con tu número de WhatsApp

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,  # Envía el mensaje a tu número de prueba
            "type": "text",
            "text": {
                "preview_url": False,
                "body": f"Prueba de carga {random.randint(1000, 9999)}"
            }
        }
        
        print(f"📤 JSON enviado a WhatsApp Webhook: {payload}", flush=True)  # 👈 Verifica que el JSON es correcto antes de enviarlo

        headers = {
            "Authorization": "Bearer EAAgxQsPPmBkBOzxQScdg4MCZByZAxr01DBR0I5mj73boDVQx75WisBo68sUYbbZCK9KZCV5Q3nyAuiDUJnxZApQpxyGqDmvpJSbY9ZCAY66ZB56VQzRoLsnkUMEI5QrCt76RBXEWVdaiJiVxlEc8Ogw7k8ZAI77jJnpDG6TnSZBYergI4q7gKvbdAoVafax1UJgB8",  # Reemplaza con tu token de Meta
            "Content-Type": "application/json"
        }
        
        self.client.post("https://graph.facebook.com/v22.0/579482118572875/messages", 
                         json=payload, headers=headers)