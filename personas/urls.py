# personas/urls.py
from django.urls import path
from .views import listar_estudiantes_con_secciones

urlpatterns = [
    path('listar-estudiantes-secciones/', listar_estudiantes_con_secciones, name='listar_estudiantes_secciones'),
]