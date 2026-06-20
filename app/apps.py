from django.apps import AppConfig
from django.conf import settings

from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        print("preparing app")
        from .models import SiteConfig
        from . import signals
        settings.SITE_CONFIG = SiteConfig.objects.first()

    # def post_ready_callback(self, sender, **kwargs):
