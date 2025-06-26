# clases/urls.py

from django.urls import path
from . import views



urlpatterns = [
    # Dashboard y gestión
    path('dashboard-profesor/', views.dashboard_profesor,      name='dashboard_profesor'),
    path('gestionar_aulas/',        views.gestionar_aulas,     name='gestionar_aulas'),
    path('gestionar_bloques_horarios/', views.gestionar_bloques_horarios, name='gestionar_bloques_horarios'),
    path('gestionar_clases/',       views.gestionar_clases,    name='gestionar_clases'),
    path('get_asignaturas_ajax/',   views.get_asignaturas_ajax,name='get_asignaturas_ajax'),
    path('get_secciones_ajax/',     views.get_secciones_ajax,  name='get_secciones_ajax'),
    path('ajax/secciones/', views.get_secciones_ajax, name='get_secciones_ajax'),
    path('ajax/secciones/', views.get_secciones_ajax, name='get_secciones_ajax'),
    # Horario del profesor
    path('mi-horario/',             views.horario_profesor,    name='horario_profesor'),
    path('instancia/<int:inst_id>/',          views.detalle_instancia,          name='detalle_instancia'),
    path('instancia/<int:inst_id>/ajax_manual/', views.ajax_asistencia_manual,    name='ajax_asistencia_manual'),
    path('instancia/<int:inst_id>/ajax_facial/', views.ajax_asistencia_facial_live, name='ajax_asistencia_facial_live'),

    # Reportes / historial
    path('finalizar-clase/<int:clase_id>/', views.finalizar_clase,    name='finalizar_clase'),
    path('historial-clases/',               views.historial_clases,  name='historial_clases'),
    path('reporte-clase/<int:clase_id>/',   views.reporte_clase,      name='reporte_clase'),


    
    path('match-face/', views.ajax_match_face, name='ajax_match_face'),

  
]
