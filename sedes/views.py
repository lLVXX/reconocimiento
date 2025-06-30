# SEDES/VIEWS.PY

from django.shortcuts import render, get_object_or_404, redirect
from .models import Sede, Carrera
from .forms import SedeForm
from core.decorators import admin_global_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CarreraForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django import forms
import requests
from django.urls import reverse
from django.contrib import messages
from requests.exceptions import RequestException
from django.db import IntegrityError
import numpy as np
import os
import tempfile
from django.conf import settings
from django.core.exceptions import ValidationError

from core.models import CustomUser
from personas.forms import EstudianteForm
from personas.models import EstudianteAsignaturaSeccion, EstudianteFoto
from django.db.models import Count  

from django.db import transaction
from core.models import CustomUser


import string


from personas.forms import ProfesorForm, EstudianteForm
from personas.models import EstudianteAsignaturaSeccion
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

import logging

from .models import Sede, Carrera, Asignatura, Seccion
from .forms import SedeForm, CarreraForm, AsignaturaForm, SeccionForm


logger = logging.getLogger(__name__)

def es_admin_global(user):
    return user.is_authenticated and user.user_type == 'admin_global'


@login_required
@admin_global_required
def gestionar_sedes(request):
    sede_id     = request.GET.get('editar')
    eliminar_id = request.GET.get('eliminar')

    # Eliminar
    if eliminar_id:
        sede = get_object_or_404(Sede, id=eliminar_id)
        sede.delete()
        messages.success(request, "Sede eliminada correctamente.")
        # Usamos el namespace 'sedes'
        return redirect('sedes:gestionar_sedes')

    # Crear o editar
    if sede_id:
        instancia = get_object_or_404(Sede, id=sede_id)
        form = SedeForm(instance=instancia)
    else:
        instancia = None
        form = SedeForm()

    if request.method == 'POST':
        if 'sede_id' in request.POST:
            instancia = get_object_or_404(Sede, id=request.POST['sede_id'])
            form = SedeForm(request.POST, instance=instancia)
        else:
            form = SedeForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Sede guardada correctamente.")
            return redirect('sedes:gestionar_sedes')
        else:
            messages.error(request, "Corrige los errores del formulario.")

    # Listado
    sedes = Sede.objects.all()
    return render(request, 'sedes/gestionar_sedes.html', {
        'form':      form,
        'sedes':     sedes,
        'editando':  instancia is not None,
        'sede_id':   sede_id or '',
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
    editar_id   = request.GET.get('editar')
    eliminar_id = request.GET.get('eliminar')

    # Eliminar carrera
    if eliminar_id:
        carrera = get_object_or_404(Carrera, id=eliminar_id, sede=request.user.workzone)
        carrera.delete()
        messages.success(request, "Carrera eliminada correctamente.")
        return redirect('sedes:gestionar_carreras')

    # Instanciar formulario (edición o creación)
    if editar_id:
        instancia = get_object_or_404(Carrera, id=editar_id, sede=request.user.workzone)
        form = CarreraForm(request.POST or None, instance=instancia)
    else:
        form = CarreraForm(request.POST or None)

    # Procesar POST (único bloque)
    if request.method == 'POST':
        if form.is_valid():
            nombre = form.cleaned_data['nombre'].strip()
            # Buscar duplicados en la misma sede
            qs = Carrera.objects.filter(nombre__iexact=nombre, sede=request.user.workzone)
            if editar_id:
                qs = qs.exclude(pk=editar_id)
            if qs.exists():
                form.add_error('nombre', 'Ya existe una carrera con ese nombre en tu sede.')
            else:
                try:
                    carrera = form.save(commit=False)
                    carrera.sede = request.user.workzone
                    carrera.save()
                except IntegrityError:
                    form.add_error('nombre', 'No se pudo guardar: nombre duplicado.')
                else:
                    messages.success(
                        request,
                        f"Carrera {'actualizada' if editar_id else 'creada'} correctamente."
                    )
                    return redirect('sedes:gestionar_carreras')
        else:
            messages.error(request, "Revisa los errores del formulario.")

    # Renderizar plantilla con listado actualizado
    carreras = Carrera.objects.filter(sede=request.user.workzone).order_by('nombre')
    return render(request, 'sedes/gestionar_carreras.html', {
        'form': form,
        'carreras': carreras,
        'editar_id': editar_id,
    })


@login_required
@admin_zona_required
def gestionar_asignaturas(request):
    editar_id    = request.GET.get("editar")
    eliminar_id  = request.GET.get("eliminar")
    carrera_id   = request.GET.get("carrera_id")

    # Listado de carreras para el dropdown
    carreras = Carrera.objects.filter(sede=request.user.workzone).order_by("nombre")

    # Eliminar asignatura y redirigir manteniendo filtro
    if eliminar_id:
        Asignatura.objects.filter(
            id=eliminar_id,
            carrera__sede=request.user.workzone
        ).delete()
        messages.success(request, "Asignatura eliminada correctamente.")
        url = reverse("sedes:gestionar_asignaturas")
        if carrera_id:
            url += f"?carrera_id={carrera_id}"
        return redirect(url)

    # Instanciar formulario para crear o editar
    if editar_id:
        instance = get_object_or_404(
            Asignatura,
            id=editar_id,
            carrera__sede=request.user.workzone
        )
        form = AsignaturaForm(
            request.POST or None,
            instance=instance,
            sede=request.user.workzone
        )
    else:
        form = AsignaturaForm(
            request.POST or None,
            sede=request.user.workzone
        )

    # Procesar POST (crear/editar)
    if request.method == 'POST':
        if form.is_valid():
            asignatura = form.save(commit=False)
            # Validación extra en creación
            if not editar_id and asignatura.carrera.sede != request.user.workzone:
                messages.error(request, "No puedes crear una asignatura en otra sede.")
            else:
                asignatura.save()
                messages.success(
                    request,
                    f"{'Asignatura actualizada' if editar_id else 'Asignatura creada'} exitosamente."
                )
                url = reverse("sedes:gestionar_asignaturas")
                if carrera_id:
                    url += f"?carrera_id={carrera_id}"
                return redirect(url)
        else:
            messages.error(request, "Revisa los errores del formulario.")

    # Construir queryset filtrado por carrera si se indicó
    qs = Asignatura.objects.filter(carrera__sede=request.user.workzone)
    if carrera_id:
        qs = qs.filter(carrera__id=carrera_id)
    asignaturas = qs.select_related('carrera', 'carrera__sede').order_by('nombre')

    return render(request, "sedes/gestionar_asignaturas.html", {
        'form':             form,
        'asignaturas':      asignaturas,
        'carreras':         carreras,
        'selected_carrera': int(carrera_id) if carrera_id else None,
        'editar_id':        editar_id,
    })


@login_required
@admin_zona_required
def gestionar_secciones(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    if eliminar_id:
        Seccion.objects.filter(id=eliminar_id, asignatura__carrera__sede=request.user.workzone).delete()
        messages.success(request, "Sección eliminada correctamente.")
        return redirect("clases:gestionar_secciones")

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
                    return redirect("clases:gestionar_secciones")
            seccion.save()
            messages.success(request, f"{'Sección actualizada' if editar_id else 'Sección creada'} exitosamente.")
            return redirect("clases:gestionar_secciones")
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
        return redirect("sedes:gestionar_profesores")

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
            return redirect("sedes:gestionar_profesores")
        else:
            messages.error(request, "Revisa los errores del formulario.")

    profesores = CustomUser.objects.filter(user_type='profesor', sede=request.user.sede).select_related('carrera')
    return render(request, "sedes/gestionar_profesores.html", {
        'form': form,
        'profesores': profesores,
        'editar_id': editar_id
    })



#####################################



















# --- AJAX: Asignaturas y Secciones por Carrera ---
@login_required
def ajax_asignaturas_secciones(request):
    carrera_id = request.GET.get('carrera_id')
    data = []
    if carrera_id:
        asignaturas = Asignatura.objects.filter(carrera_id=carrera_id)
        for asignatura in asignaturas:
            secciones = Seccion.objects.filter(asignatura=asignatura).values('id', 'nombre')
            data.append({
                'asignatura': asignatura.nombre,
                'secciones': list(secciones),
            })
    return JsonResponse({'asignaturas': data})









##################################









@login_required
def ajax_asignaturas_secciones(request):
    carrera_id = request.GET.get('carrera_id')
    data = []
    if carrera_id:
        asignaturas = Asignatura.objects.filter(carrera_id=carrera_id)
        for asignatura in asignaturas:
            secciones = Seccion.objects.filter(asignatura=asignatura).values('id', 'nombre')
            data.append({
                'asignatura': asignatura.nombre,
                'secciones': list(secciones),
            })
    return JsonResponse({'asignaturas': data})




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
    

###################################################################
###                        ARCFACE                              ###
###################################################################

MICRO_URL = settings.ARC_FACE_URL.rstrip('/')

@login_required
@admin_zona_required
def gestionar_estudiantes(request):
    editar_id    = request.GET.get('editar')
    eliminar_id  = request.GET.get('eliminar')
    carrera_id   = request.GET.get('carrera_id')

    # Eliminar
    if eliminar_id:
        CustomUser.objects.filter(id=eliminar_id, user_type='estudiante').delete()
        messages.success(request, 'Estudiante eliminado correctamente.')
        return redirect('sedes:gestionar_estudiantes')

    # Crear / editar formulario
    if editar_id:
        alumno = get_object_or_404(CustomUser, id=editar_id, user_type='estudiante')
        form = EstudianteForm(request.POST or None, request.FILES or None, instance=alumno, user=request.user)
    else:
        alumno = None
        form = EstudianteForm(request.POST or None, request.FILES or None, user=request.user)

    # Procesar POST
    if request.method == 'POST':
        if form.is_valid():
            try:
                with transaction.atomic():
                    alumno = form.save()
                    img = form.cleaned_data['imagen']
                    img.seek(0)
                    files = {'file': (img.name, img.read(), img.content_type)}
                    resp = requests.post(f"{MICRO_URL}/generar_embedding/", files=files, timeout=15)
                    data = resp.json()
                    if not data.get('ok'):
                        raise ValidationError(data.get('msg', 'No se detectó rostro.'))
                    embedding = data['embedding']

                    # Guardar foto-base y embedding
                    EstudianteFoto.objects.filter(estudiante=alumno, es_base=True).delete()
                    EstudianteFoto.objects.create(
                        estudiante=alumno,
                        imagen=form.cleaned_data['imagen'],
                        embedding=embedding,
                        es_base=True
                    )

                    # Asignaciones automáticas
                    for asig in Asignatura.objects.filter(carrera=alumno.carrera):
                        seccs = Seccion.objects.filter(asignatura=asig) \
                            .annotate(num_est=Count('relaciones_estudiantes_asignatura'))
                        sec = next((s for s in seccs if s.num_est < 30), None)
                        if not sec:
                            sec = Seccion.objects.create(
                                nombre=f"{asig.nombre[:6]}-{asig.id}A",
                                asignatura=asig
                            )
                        EstudianteAsignaturaSeccion.objects.get_or_create(
                            estudiante=alumno,
                            asignatura=asig,
                            defaults={'seccion': sec}
                        )

                messages.success(request, 'Estudiante guardado y embedding generado.')
                return redirect('sedes:gestionar_estudiantes')

            except ValidationError as e:
                messages.error(request, e.message)
            except Exception as e:
                messages.error(request, f'Error inesperado: {e}')
        else:
            messages.error(request, 'Corrige los errores del formulario.')

    # Construir query de estudiantes con filtro
    qs = CustomUser.objects.filter(user_type='estudiante', sede=request.user.sede)
    if carrera_id:
        qs = qs.filter(carrera_id=carrera_id)

    estudiantes = qs.order_by('last_name', 'first_name')

    # Para el filtro en el template
    carreras = Carrera.objects.filter(sede=request.user.sede).order_by('nombre')
    selected_carrera = int(carrera_id) if carrera_id else None

    # Fotos base y asignaciones
    fotos_base = {
        f.estudiante_id: f.imagen.url
        for f in EstudianteFoto.objects.filter(estudiante__in=estudiantes, es_base=True)
    }
    relaciones = EstudianteAsignaturaSeccion.objects.filter(estudiante__in=estudiantes)
    asignaciones = {}
    for rel in relaciones:
        asignaciones.setdefault(rel.estudiante_id, []).append(
            f"{rel.asignatura.nombre}: {rel.seccion.nombre}"
        )

    return render(request, 'sedes/gestionar_estudiantes.html', {
        'form': form,
        'estudiantes': estudiantes,
        'fotos_base': fotos_base,
        'asignaciones': asignaciones,
        'editar_id': editar_id,
        'carreras': carreras,
        'selected_carrera': selected_carrera,
    })

def obtener_embedding(imagen_source):
    """
    Llama al microservicio ONNX/ArcFace para generar el embedding.
    Guarda la última respuesta JSON en _last_response para depuración.
    """
    url = settings.ARC_FACE_URL.rstrip("/") + "/generar_embedding/"
    logger.debug("Llamando a %s", url)

    # Preparar payload
    if hasattr(imagen_source, 'read'):
        imagen_source.seek(0)
        contenido = imagen_source.read()
        filename = imagen_source.name
        content_type = imagen_source.content_type
    else:
        filename = imagen_source.split('/')[-1]
        content_type = 'application/octet-stream'
        with open(imagen_source, 'rb') as f:
            contenido = f.read()

    logger.debug("Payload preparado: filename=%s, content_type=%s, bytes=%d",
                 filename, content_type, len(contenido))

    files = {'file': (filename, contenido, content_type)}
    data = None

    try:
        resp = requests.post(url, files=files, timeout=15)
        logger.debug("Respuesta HTTP %d", resp.status_code)
        resp.raise_for_status()
        text = resp.text
        logger.debug("Contenido de respuesta: %s", text[:500])
        data = resp.json()
        setattr(obtener_embedding, "_last_response", data)
        logger.debug("JSON parseado: %s", data)

        if data.get('ok') and 'embedding' in data:
            emb = np.array(data['embedding'], dtype=np.float32)
            logger.debug("Embedding generado de longitud %d", len(emb))
            return emb

    except requests.Timeout:
        logger.exception("Timeout al conectar con el microservicio")
    except requests.HTTPError as e:
        logger.exception("Error HTTP %s", e)
    except ValueError as e:
        logger.exception("JSON inválido recibida")
    except Exception as e:
        logger.exception("Error inesperado en obtener_embedding")

    setattr(obtener_embedding, "_last_response", data)
    return None















@login_required
@admin_zona_required
def sync_secciones(request, est_id):
    alumno = get_object_or_404(CustomUser, id=est_id, user_type='estudiante', sede=request.user.sede)

    # Todas las asignaturas de su carrera
    asignaturas = Asignatura.objects.filter(carrera=alumno.carrera)

    for asig in asignaturas:
        # ¿Ya está inscrito?
        exists = EstudianteAsignaturaSeccion.objects.filter(
            estudiante=alumno, asignatura=asig
        ).exists()
        if not exists:
            # buscamos sección con menos alumnos
            seccs = (Seccion.objects
                     .filter(asignatura=asig)
                     .annotate(num_est=Count('relaciones_estudiantes_asignatura'))
                     .order_by('num_est'))
            if seccs:
                sec = seccs.first()
            else:
                sec = Seccion.objects.create(
                    nombre=f"{asig.nombre[:6]}-{asig.id}A",
                    asignatura=asig
                )
            EstudianteAsignaturaSeccion.objects.create(
                estudiante=alumno,
                asignatura=asig,
                seccion=sec
            )

    messages.success(request, f'Secciones sincronizadas para {alumno.get_full_name()}.')
    return redirect('gestionar_estudiantes')


@login_required
@admin_zona_required
def sync_todas_secciones(request):
    """
    Recorre todos los estudiantes de la sede del admin_zona y auto-inscribe
    en cualquier asignatura de su carrera que aún no tengan asignada.
    """
    sede = request.user.sede
    estudiantes = CustomUser.objects.filter(user_type='estudiante', sede=sede)

    for alumno in estudiantes:
        asignaturas = Asignatura.objects.filter(carrera=alumno.carrera)
        for asig in asignaturas:
            if not EstudianteAsignaturaSeccion.objects.filter(
                   estudiante=alumno, asignatura=asig
               ).exists():
                # elige la sección con menos estudiantes o crea una nueva
                seccs = (Seccion.objects
                         .filter(asignatura=asig)
                         .annotate(num_est=Count('relaciones_estudiantes_asignatura'))
                         .order_by('num_est'))
                if seccs:
                    sec = seccs.first()
                else:
                    sec = Seccion.objects.create(
                        nombre=f"{asig.nombre[:6]}-{asig.id}A", asignatura=asig
                    )
                EstudianteAsignaturaSeccion.objects.create(
                    estudiante=alumno, asignatura=asig, seccion=sec
                )

    messages.success(request, "Secciones sincronizadas para todos los estudiantes.")
    return redirect('sedes:gestionar_estudiantes')