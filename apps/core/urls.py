from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('acerca/', views.about_view, name='about'),
    path('modelo/', views.model_info_view, name='model_info'),
]
