"""
App configuration for the main app within the Ada mock project.
"""

from django.apps import AppConfig  # type: ignore


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    verbose_name = 'Ada Mock'
