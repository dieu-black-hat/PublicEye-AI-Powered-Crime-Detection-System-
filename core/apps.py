from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'PublicEye Crime Detection System'
    
    def ready(self):
        # Import signals or start background tasks here if needed
        # import core.signals
        pass