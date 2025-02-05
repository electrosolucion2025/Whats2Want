import requests

def send_whatsapp_message(to_phone_number, ai_response, tenant):
    url = f"https://graph.facebook.com/v15.0/{tenant.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {tenant.whatsapp_access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",    
        "recipient_type": "individual",
        "to": to_phone_number,
        "type": "text",
        "text": {
            "body": ai_response
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()