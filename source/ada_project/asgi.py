"""
ASGI config for Ada mock project.

It exposes the ASGI callable as a module-level variable named ``application``.

This file is a near verbatim copy of the default created by Django's
``django-admin startproject`` command. It exists here to allow the project
to be run with an ASGI server once Django is installed.
"""

import os
from django.core.asgi import get_asgi_application  # type: ignore


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ada_project.settings')

application = get_asgi_application()
