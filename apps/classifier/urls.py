from django.urls import path
from . import views

app_name = 'classifier'

urlpatterns = [
    path('', views.analyze_view, name='analyze'),
    path('demo/<str:demo_name>/', views.analyze_demo_view, name='analyze_demo'),
    path('resultado/<int:record_id>/', views.result_detail_view, name='result_detail'),
    path('resultado/<int:record_id>/pdf/', views.download_pdf_report_view, name='download_pdf'),
]
