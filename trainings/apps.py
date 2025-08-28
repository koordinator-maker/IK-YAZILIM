from django.apps import AppConfig

class TrainingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trainings"

    def ready(self):
        # Sinyalleri yükle
        from . import signals  # noqa: F401
