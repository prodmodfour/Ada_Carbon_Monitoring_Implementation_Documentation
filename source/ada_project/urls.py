"""
URL configuration for Ada mock project.

The ``urlpatterns`` list routes URLs to views. See Django documentation
for details about how to write routes. This configuration delegates
all routing to the ``main`` application so that view logic lives in
``main.views``.
"""

from django.urls import include, path  # type: ignore

urlpatterns = [
    path('', include('main.urls')),
]
