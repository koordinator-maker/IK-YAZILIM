# trainings/apps.py
from django.apps import AppConfig


class TrainingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trainings"
    verbose_name = "Trainings / HR-LMS"

    def ready(self):
        # Mevcut sinyaller (silme!)
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Sinyaller yoksa sessizce geç
            pass

        # Boot report (her açılışta rapor üretir)
        try:
            from .bootreport import safe_write_boot_report
            safe_write_boot_report()
        except Exception:
            # Rapor üretilemezse uygulamayı düşürmeyelim
            pass
