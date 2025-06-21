# clases/urls.py

from django.urls import path
from . import views

urlpatterns = [

    path('dashboard-profesor/', views.dashboard_profesor, name='dashboard_profesor'),






    path('gestionar_aulas/', views.gestionar_aulas, name='gestionar_aulas'),
   
    path('gestionar_bloques_horarios/', views.gestionar_bloques_horarios, name='gestionar_bloques_horarios'),
   
    path('get_asignaturas_ajax/', views.get_asignaturas_ajax, name='get_asignaturas_ajax'),
    path('get_secciones_ajax/', views.get_secciones_ajax, name='get_secciones_ajax'),

   
    path('gestionar_clases/', views.gestionar_clases, name='gestionar_clases'),
    path('get_asignaturas_ajax/', views.get_asignaturas_ajax, name='get_asignaturas_ajax'),
    path('get_secciones_ajax/', views.get_secciones_ajax, name='get_secciones_ajax'),


    path('detalle-clase/<int:clase_id>/', views.detalle_clase, name='detalle_clase'),
    path('ajax-asistencia-live/<int:clase_id>/', views.ajax_asistencia_facial_live, name='ajax_asistencia_facial_live'),
    path('ajax-asistencia-manual/<int:clase_id>/', views.ajax_asistencia_manual, name='ajax_asistencia_manual'),

    path('historial-clases/', views.historial_clases, name='historial_clases'),

    path('reporte-clase/<int:clase_id>/', views.reporte_clase, name='reporte_clase'),
    path('clases/historial/', views.historial_clases, name='historial_clases'),
    path('finalizar-clase/<int:clase_id>/', views.finalizar_clase, name='finalizar_clase'),


    path('mi-horario/', views.horario_profesor, name='horario_profesor'),


   


]
