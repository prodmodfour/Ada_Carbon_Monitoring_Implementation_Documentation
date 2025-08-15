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
    # Route for selecting an instrument when creating a new workspace.
    # This page displays a grid of available instruments whose
    # contents vary depending on the selected data source (e.g. ISIS,
    # CLF or Diamond).
    path('analysis/<str:source>/instruments/', views.instruments, name='instruments'),

    path('analysis/<str:source>/instruments/<str:instrument>/', 
         views.instrument_detail, 
         name='instrument_detail'),
    path('analysis/<str:source>/workspaces/<str:ws_id>/', views.workspace_detail, name='workspace_detail'),
    path('api/ci', views.ci_proxy, name='ci_proxy'),
    path('api/project-usage', views.project_usage_api, name='project_usage_api'),
    path('api/sci-score', views.sci_score_api, name='sci_score_api'),


]
