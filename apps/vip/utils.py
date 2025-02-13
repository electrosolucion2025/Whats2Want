from .models import VIPAccess

def is_vip(phone_number, tenant):
    return VIPAccess.objects.filter(contact__phone_number=phone_number, tenant=tenant).exists()
