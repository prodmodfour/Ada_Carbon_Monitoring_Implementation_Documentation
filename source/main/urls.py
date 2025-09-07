"""
URL declarations for the main app.

These routes correspond to the mock interface's pages. The ``home``
view renders the landing page with the dataset cards, and the
``analysis`` view renders a generic analysis page whose heading changes
based on the selected data source. Additional routes can be added
easily as the mock evolves.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('analysis/<str:source>/', views.analysis, name='analysis'),
    

    path('analysis/plot/<str:source>/<str:range_key>/<str:view_type>/', 
         views.get_usage_plot, 
         name='get_usage_plot'),

    path('analysis/<str:source>/instruments/', views.instruments, name='instruments'),
    path('analysis/<str:source>/instruments/<str:instrument>/', 
         views.instrument_detail, 
         name='instrument_detail'),
    path('analysis/<str:source>/workspaces/<str:ws_id>/', views.workspace_detail, name='workspace_detail'),
    
    # API routes
    path('api/ci', views.ci_proxy, name='ci_proxy'),
    path('api/sci-score', views.sci_score_api, name='sci_score_api'),
    path('api/ghg-score', views.ghg_score_api, name='ghg_score_api'),


]