#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import django
from django.contrib.auth import get_user_model

def create_superuser():
    """Crea un superusuario automáticamente si no existe."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "w2w.settings")
    django.setup()  # Asegurar que Django está cargado antes de acceder a los modelos

    User = get_user_model()
    if not User.objects.filter(username=os.getenv("DJANGO_ADMIN_USER")).exists():
        User.objects.create_superuser(
            username=os.getenv("DJANGO_ADMIN_USER"),
            email=os.getenv("DJANGO_ADMIN_EMAIL"),
            password=os.getenv("DJANGO_ADMIN_PASSWORD")
        )
        print("✅ Superusuario creado automáticamente.")

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'w2w.settings')
    
    # Crear superusuario si está habilitado
    if os.getenv("AUTO_CREATE_SUPERUSER") == "True":
        create_superuser()

    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(sys.argv)
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

if __name__ == '__main__':
    main()
