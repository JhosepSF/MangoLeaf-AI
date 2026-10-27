from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    path('', views.history_list_view, name='history_list'),
    path('eliminar/<int:record_id>/', views.history_delete_view, name='history_delete'),
]
