from django.urls import path
from .views import portal_inicio, dashboard_admin_global, cerrar_sesion,gestionar_admin_zona,dashboard_admin_zona
from .views import redirigir_por_rol, dashboard_admin_zona

urlpatterns = [
    path('', portal_inicio, name='portal_inicio'),  # Muestra el login siempre
    path('redirigir/', redirigir_por_rol, name='redirigir_por_rol'),

    path('dashboard/', dashboard_admin_global, name='dashboard_admin_global'),
    path('logout/', cerrar_sesion, name='logout'),

    path('admin-zona/', dashboard_admin_zona, name='dashboard_admin_zona'),
    path('admin-global/gestionar_admin_zona/', gestionar_admin_zona, name='gestionar_admin_zona'),

]