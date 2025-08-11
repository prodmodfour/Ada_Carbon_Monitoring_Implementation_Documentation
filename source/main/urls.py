"""
URL declarations for the main app.

These routes correspond to the mock interface's pages. The ``home``
view renders the landing page with the dataset cards, and the
``analysis`` view renders a generic analysis page whose heading changes
based on the selected data source. Additional routes can be added
easily as the mock evolves.
"""

from django.urls import path  # type: ignore
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('analysis/<str:source>/', views.analysis, name='analysis'),
]
