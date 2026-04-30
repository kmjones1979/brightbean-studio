from django.apps import AppConfig


class GTMConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gtm"
    verbose_name = "GTM Planning"

    def ready(self):
        from apps.gtm import signals  # noqa: F401
