# SEDES/VIEWS.PY

from django.shortcuts import render, get_object_or_404, redirect
from .models import Sede, Carrera
from .forms import SedeForm
from core.utils import admin_global_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CarreraForm
from django.contrib.auth.decorators import login_required, user_passes_test

from django.db.models import Count  

from django.db import transaction
from core.models import CustomUser


import string


from personas.forms import ProfesorForm, EstudianteForm
from personas.models import EstudianteAsignaturaSeccion
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404



from .models import Sede, Carrera, Asignatura, Seccion
from .forms import SedeForm, CarreraForm, AsignaturaForm, SeccionForm


def es_admin_global(user):
    return user.is_authenticated and user.user_type == 'admin_global'


@admin_global_required
def gestionar_sedes(request):
    sede_id = request.GET.get('editar')
    eliminar_id = request.GET.get('eliminar')

    if eliminar_id:
        sede = get_object_or_404(Sede, id=eliminar_id)
        sede.delete()
        messages.success(request, "Sede eliminada correctamente.")
        return redirect('gestionar_sedes')

    if sede_id:
        sede = get_object_or_404(Sede, id=sede_id)
        form = SedeForm(instance=sede)
    else:
        form = SedeForm()

    if request.method == 'POST':
        if 'sede_id' in request.POST:
            sede = get_object_or_404(Sede, id=request.POST['sede_id'])
            form = SedeForm(request.POST, instance=sede)
        else:
            form = SedeForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Sede guardada correctamente.")
            return redirect('gestionar_sedes')

    sedes = Sede.objects.all()
    return render(request, 'sedes/gestionar_sedes.html', {
        'form': form,
        'sedes': sedes,
        'editando': sede_id is not None,
    })



###########################################



def admin_zona_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'admin_zona':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Acceso restringido.")
        return redirect("portal_inicio")
    return wrapper


@login_required
@admin_zona_required
def gestionar_carreras(request):
    editar_id = request.GET.get('editar')
    eliminar_id = request.GET.get('eliminar')

    if eliminar_id:
        carrera = get_object_or_404(Carrera, id=eliminar_id, sede=request.user.workzone)
        carrera.delete()
        messages.success(request, "Carrera eliminada correctamente.")
        return redirect('gestionar_carreras')

    if editar_id:
        instancia = get_object_or_404(Carrera, id=editar_id, sede=request.user.workzone)
        form = CarreraForm(request.POST or None, instance=instancia)
    else:
        form = CarreraForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        carrera = form.save(commit=False)
        carrera.sede = request.user.workzone
        carrera.save()
        messages.success(request, f"Carrera {'actualizada' if editar_id else 'creada'} correctamente.")
        return redirect('gestionar_carreras')

    carreras = Carrera.objects.filter(sede=request.user.workzone).order_by('nombre')
    return render(request, 'sedes/gestionar_carreras.html', {
        'form': form,
        'carreras': carreras,
        'editar_id': editar_id
    })


@login_required
@admin_zona_required
def gestionar_asignaturas(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    if eliminar_id:
        Asignatura.objects.filter(id=eliminar_id, carrera__sede=request.user.workzone).delete()
        messages.success(request, "Asignatura eliminada correctamente.")
        return redirect("gestionar_asignaturas")

    if editar_id:
        instance = get_object_or_404(Asignatura, id=editar_id, carrera__sede=request.user.workzone)
        form = AsignaturaForm(request.POST or None, instance=instance, sede=request.user.workzone)
    else:
        form = AsignaturaForm(request.POST or None, sede=request.user.workzone)

    if request.method == 'POST':
        if form.is_valid():
            asignatura = form.save(commit=False)
            if not editar_id:
                # Solo permitir carreras de su sede
                if asignatura.carrera.sede != request.user.workzone:
                    messages.error(request, "No puedes crear una asignatura en otra sede.")
                    return redirect("gestionar_asignaturas")
            asignatura.save()
            messages.success(request, f"{'Asignatura actualizada' if editar_id else 'Asignatura creada'} exitosamente.")
            return redirect("gestionar_asignaturas")
        else:
            messages.error(request, "Revisa los errores del formulario.")

    asignaturas = Asignatura.objects.filter(carrera__sede=request.user.workzone).select_related('carrera', 'carrera__sede')
    return render(request, "sedes/gestionar_asignaturas.html", {
        'form': form,
        'asignaturas': asignaturas,
        'editar_id': editar_id
    })


@login_required
@admin_zona_required
def gestionar_secciones(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    if eliminar_id:
        Seccion.objects.filter(id=eliminar_id, asignatura__carrera__sede=request.user.workzone).delete()
        messages.success(request, "Sección eliminada correctamente.")
        return redirect("gestionar_secciones")

    if editar_id:
        instance = get_object_or_404(Seccion, id=editar_id, asignatura__carrera__sede=request.user.workzone)
        form = SeccionForm(request.POST or None, instance=instance, sede=request.user.workzone)
    else:
        form = SeccionForm(request.POST or None, sede=request.user.workzone)

    if request.method == 'POST':
        if form.is_valid():
            seccion = form.save(commit=False)
            if not editar_id:
                if seccion.asignatura.carrera.sede != request.user.workzone:
                    messages.error(request, "No puedes crear una sección en otra sede.")
                    return redirect("gestionar_secciones")
            seccion.save()
            messages.success(request, f"{'Sección actualizada' if editar_id else 'Sección creada'} exitosamente.")
            return redirect("gestionar_secciones")
        else:
            messages.error(request, "Revisa los errores del formulario.")

    secciones = Seccion.objects.filter(asignatura__carrera__sede=request.user.workzone).select_related('asignatura', 'asignatura__carrera', 'asignatura__carrera__sede')
    return render(request, "sedes/gestionar_secciones.html", {
        'form': form,
        'secciones': secciones,
        'editar_id': editar_id
    })





from personas.forms import ProfesorForm
from core.models import CustomUser
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test

def is_admin_zona(user):
    return user.is_authenticated and user.user_type == 'admin_zona'



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import CustomUser
from personas.forms import ProfesorForm
from sedes.models import Carrera, Asignatura

def admin_zona_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'admin_zona':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Acceso restringido.")
        return redirect("portal_inicio")
    return wrapper

@login_required
@admin_zona_required
def gestionar_profesores(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    if eliminar_id:
        profesor = get_object_or_404(CustomUser, id=eliminar_id, user_type='profesor')
        profesor.delete()
        messages.success(request, "Profesor eliminado correctamente.")
        return redirect("gestionar_profesores")

    if editar_id:
        instance = get_object_or_404(CustomUser, id=editar_id, user_type='profesor')
        form = ProfesorForm(request.POST or None, instance=instance, user=request.user)
    else:
        form = ProfesorForm(request.POST or None, user=request.user)

    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            nombre = form.cleaned_data['nombre'].strip().lower()
            apellido = form.cleaned_data['apellido'].strip().lower()
            rut = form.cleaned_data['rut']
            carrera = form.cleaned_data['carrera']

            nombre_corto = nombre[:2]
            sede_nombre = request.user.sede.nombre.lower().replace(" ", "")
            username_base = f"{nombre_corto}{apellido}"
            email_base = f"{nombre_corto}.{apellido}@{sede_nombre}.com"

            username_final = username_base
            email_final = email_base

            i = 1
            while CustomUser.objects.filter(username=username_final).exists():
                username_final = f"{username_base}{i}"
                i += 1

            i = 1
            while CustomUser.objects.filter(email=email_final).exists():
                email_final = f"{nombre_corto}.{apellido}{i}@{sede_nombre}.com"
                i += 1

            instance.username = username_final
            instance.email = email_final
            instance.first_name = nombre
            instance.last_name = apellido
            instance.user_type = 'profesor'
            instance.sede = request.user.sede
            instance.carrera = carrera
            instance.rut = rut

            if not editar_id:
                instance.set_password('12345678')

            instance.save()
            form.save_m2m()  # Guardar asignaturas
            messages.success(request, f"{'Actualizado' if editar_id else 'Creado'} correctamente: {username_final}")
            return redirect("gestionar_profesores")
        else:
            messages.error(request, "Revisa los errores del formulario.")

    profesores = CustomUser.objects.filter(user_type='profesor', sede=request.user.sede).select_related('carrera')
    return render(request, "sedes/gestionar_profesores.html", {
        'form': form,
        'profesores': profesores,
        'editar_id': editar_id
    })



#####################################



@login_required
def gestionar_estudiantes(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    if eliminar_id:
        estudiante = get_object_or_404(CustomUser, id=eliminar_id, user_type='estudiante')
        estudiante.delete()
        messages.success(request, "Estudiante eliminado correctamente.")
        return redirect('gestionar_estudiantes')

    if editar_id:
        instancia = get_object_or_404(CustomUser, id=editar_id, user_type='estudiante')
        form = EstudianteForm(request.POST or None, request.FILES or None, instance=instancia, user=request.user)
    else:
        instancia = None
        form = EstudianteForm(request.POST or None, request.FILES or None, user=request.user)

    if request.method == 'POST':
        if form.is_valid():
            estudiante = form.save()
            messages.success(request, "Estudiante guardado exitosamente.")
            return redirect('gestionar_estudiantes')
        else:
            messages.error(request, "Error al procesar el formulario. Revisa los datos.")

    estudiantes = CustomUser.objects.filter(user_type='estudiante', sede=request.user.sede)

    return render(request, 'sedes/gestionar_estudiantes.html', {
        'form': form,
        'estudiantes': estudiantes,
        'editar_id': editar_id,
    })

def generar_embedding_estudiante(estudiante):
    print(f"[DEBUG] Generando embedding para {estudiante.nombre} {estudiante.apellido}")


####################################

@login_required
@admin_zona_required
def resumen_estudiantes_por_seccion(request):
    secciones = Seccion.objects.select_related(
        'asignatura__carrera__sede'
    ).annotate(
        cantidad_estudiantes=Count('estudiantes')
    )

    contexto = {'secciones': secciones}
    return render(request, 'clases/resumen_estudiantes.html', contexto)