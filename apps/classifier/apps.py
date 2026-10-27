from django.apps import AppConfig

class ClassifierConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.classifier'
    verbose_name = 'Clasificador Fitosanitario'

    def ready(self):
        # Opcional: precargar el modelo en el inicio del proceso de Django
        # si no se está ejecutando un comando de migración
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv or 'wsgi' in sys.argv:
            try:
                from .services.inference import get_inference_engine
                get_inference_engine()
            except Exception:
                pass
