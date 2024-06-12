from django.apps import AppConfig


class BabelfishConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "babelfish"

    def ready(self):
        # We patch Wagtail to inject the copy_for_translation_done signal.
        from . import signals  # noqa
