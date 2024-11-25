from django.apps import AppConfig

# Communications app config
class CommunicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "communications"
    def ready(self):
        import communications.signals