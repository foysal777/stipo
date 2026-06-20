from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        print("preparing app")
        from . import signals
        self._load_site_config()

    def _load_site_config(self):
        """
        Load SiteConfig from DB into settings.SITE_CONFIG.
        Wrapped in try/except so it doesn't crash on a fresh DB
        (before migrations have created the table).
        """
        from .models import SiteConfig
        try:
            settings.SITE_CONFIG = SiteConfig.objects.first()
        except Exception:
            # Table doesn't exist yet (first run before migrate)
            # The CMD in Dockerfile runs migrate first, then gunicorn,
            # so by the time gunicorn starts this will succeed.
            settings.SITE_CONFIG = None
