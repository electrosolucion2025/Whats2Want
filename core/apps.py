from django.apps import AppConfig
import importlib.util
import sys
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Asegurar que Django puede encontrar el módulo correctamente
        module_path = os.path.join(os.path.dirname(__file__), 'global_admin.py')
        module_name = 'core.global_admin'

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
