from django.urls import path
from . import views

urlpatterns = [
     path('gestionar-bloques-horarios/', views.gestionar_bloques_horarios, name='gestionar_bloques_horarios'),
     path('gestionar-aulas/', views.gestionar_aulas, name='gestionar_aulas'),
     path('gestionar-clases/', views.gestionar_clases, name='gestionar_clases'),
     path('ajax/secciones-por-carrera/', views.ajax_secciones_por_carrera, name='ajax_secciones_por_carrera'),
     path('resumen-secciones/', views.resumen_estudiantes_por_seccion, name='resumen_secciones'),
    

    path('ajax/get-asignaturas/', views.get_asignaturas_ajax, name='get_asignaturas_ajax'),
    path('ajax/get-secciones/', views.get_secciones_ajax, name='get_secciones_ajax'),




     ################3
     path('dashboard-profesor/', views.dashboard_profesor, name='dashboard_profesor'),
     #######################
     path('detalle-clase/<int:clase_id>/', views.detalle_clase, name='detalle_clase'),
     #######################
     path('api/get-embeddings/<int:clase_id>/', views.api_get_embeddings, name='api_get_embeddings'),




]