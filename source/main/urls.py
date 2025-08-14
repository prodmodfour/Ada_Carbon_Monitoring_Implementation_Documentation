

from django.urls import path  
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('analysis/<str:source>/', views.analysis, name='analysis'),

    path('analysis/<str:source>/instruments/', views.instruments, name='instruments'),

    path('analysis/<str:source>/instruments/<str:instrument>/', 
         views.instrument_detail, 
         name='instrument_detail'),


    path('data-display-catalogue/',
        views.data_display_catalogue,
        name='data_display_catalogue'),
]
