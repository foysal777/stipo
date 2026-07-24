from django.apps import AppConfig
from django.conf import settings
from django.core.management import call_command
from django.db.models.signals import post_migrate


def auto_create_cache_table_and_reset_stuck_uploads(sender, **kwargs):
    """Ensure database cache table exists and reset stuck uploads after migrations run."""
    try:
        call_command('createcachetable')
    except Exception as e:
        print(f"Notice: auto createcachetable error: {e}")

    try:
        from .models import DatasetUpload
        stuck_count = DatasetUpload.objects.filter(upload_in_progress=True).update(
            upload_in_progress=False,
            upload_status='failed',
            upload_error_message='Interrupted by server restart or unexpected shutdown.'
        )
        if stuck_count:
            print(f"🔄 Auto-reset {stuck_count} stuck dataset upload(s) on post-migrate.")
    except Exception as e:
        print(f"Notice: auto reset dataset upload error: {e}")


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        print("preparing app")
        from . import signals
        post_migrate.connect(auto_create_cache_table_and_reset_stuck_uploads, sender=self)
        self._load_site_config()
        self._reset_stuck_dataset_uploads()

    def _reset_stuck_dataset_uploads(self):
        """Reset upload_in_progress flags left True due to server restarts."""
        try:
            from .models import DatasetUpload
            stuck_count = DatasetUpload.objects.filter(upload_in_progress=True).update(
                upload_in_progress=False,
                upload_status='failed',
                upload_error_message='Interrupted by server restart or unexpected shutdown.'
            )
            if stuck_count:
                print(f"🔄 Auto-reset {stuck_count} stuck dataset upload(s) on server startup.")
        except Exception:
            pass

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
