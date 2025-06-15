# personas/views.py

from django.contrib.auth.decorators import login_required
from core.decorators import admin_zona_required
from django.shortcuts import render
from core.models import CustomUser
from personas.models import EstudianteAsignaturaSeccion

@login_required
@admin_zona_required
def listar_estudiantes_con_secciones(request):
    estudiantes = CustomUser.objects.filter(user_type='estudiante', sede=request.user.sede)

    # Preparamos la estructura: {estudiante: [(asignatura, seccion), ...]}
    data = []
    for estudiante in estudiantes:
        relaciones = EstudianteAsignaturaSeccion.objects.filter(estudiante=estudiante).select_related('asignatura', 'seccion')
        asignaturas_y_secciones = [
            (rel.asignatura.nombre, rel.seccion.nombre) for rel in relaciones
        ]
        data.append({
            'estudiante': estudiante,
            'asignaturas_secciones': asignaturas_y_secciones
        })

    return render(request, 'personas/listar_estudiantes_con_secciones.html', {
        'data': data
    })
