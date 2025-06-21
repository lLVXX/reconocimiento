from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.decorators import admin_zona_required, admin_global_required, profesor_required
from django.contrib import messages
from .models import BloqueHorario, Aula, Clase, AsistenciaClase
from .forms import BloqueHorarioForm, AulaForm, ClaseForm
from sedes.models import Seccion, Asignatura, Carrera
from personas.models import EstudianteAsignaturaSeccion
from core.models import CustomUser, SemanaAcademica, CalendarioAcademico
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import requests
from datetime import timedelta
from django import forms
import io
import base64
import json
from django.db import transaction
# ========== CONFIGURACIÓN ARC FACE ==========
ARCFACE_URL = "http://localhost:8001/match_faces/"

##############################################
# CRUD BLOQUES HORARIOS
##############################################
@login_required
@admin_zona_required
def gestionar_bloques_horarios(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")
    if eliminar_id:
        BloqueHorario.objects.filter(id=eliminar_id).delete()
        messages.success(request, "Bloque eliminado correctamente.")
        return redirect('gestionar_bloques_horarios')
    if editar_id:
        bloque = get_object_or_404(BloqueHorario, id=editar_id)
        form = BloqueHorarioForm(request.POST or None, instance=bloque)
    else:
        form = BloqueHorarioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"{'Actualizado' if editar_id else 'Creado'} correctamente.")
        return redirect('gestionar_bloques_horarios')
    bloques = BloqueHorario.objects.all().order_by('hora_inicio')
    return render(request, 'clases/gestionar_bloques_horarios.html', {
        'form': form,
        'bloques': bloques,
        'editar_id': editar_id,
    })

##############################################
# CRUD AULAS
##############################################
@login_required
@admin_zona_required
def gestionar_aulas(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")
    if eliminar_id:
        aula = get_object_or_404(Aula, id=eliminar_id, sede=request.user.sede)
        aula.delete()
        messages.success(request, "Aula eliminada correctamente.")
        return redirect("gestionar_aulas")
    if editar_id:
        instancia = get_object_or_404(Aula, id=editar_id, sede=request.user.sede)
        form = AulaForm(request.POST or None, instance=instancia)
    else:
        form = AulaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        aula = form.save(commit=False)
        aula.sede = request.user.sede
        aula.save()
        messages.success(request, f"{'Actualizada' if editar_id else 'Creada'} correctamente.")
        return redirect("gestionar_aulas")
    aulas = Aula.objects.filter(sede=request.user.sede).order_by('numero_sala')
    return render(request, 'clases/gestionar_aulas.html', {
        'form': form,
        'aulas': aulas,
        'editar_id': editar_id,
    })

##############################################
# CRUD CLASES — VISUAL / TABLERO SEMANAL
##############################################










@login_required
def gestionar_clases(request):
    print("\n---- [gestionar_clases] ----")
    user = request.user
    es_admin_zona = user.user_type == 'admin_zona'
    profesores = CustomUser.objects.filter(
        user_type='profesor',
        sede=user.sede if es_admin_zona else None
    ).order_by('last_name')

    bloques = BloqueHorario.objects.order_by('hora_inicio')
    dias = ['LU', 'MA', 'MI', 'JU', 'VI', 'SA']
    dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

    selected_profesor_id = request.GET.get('profesor') or request.POST.get('profesor')
    selected_profesor = CustomUser.objects.filter(id=selected_profesor_id).first() if selected_profesor_id else None

    editar_id = request.GET.get('editar')
    eliminar_id = request.GET.get('eliminar')

    form = None
    modo_edicion = False

    # --- ELIMINAR ---
    if eliminar_id and selected_profesor:
        clase = get_object_or_404(Clase, id=eliminar_id, profesor=selected_profesor)
        clase.delete()
        messages.success(request, "Clase eliminada correctamente.")
        return redirect(f"{reverse('gestionar_clases')}?profesor={selected_profesor.id}")

    # --- EDITAR ---
    if editar_id and selected_profesor:
        clase = get_object_or_404(Clase, id=editar_id, profesor=selected_profesor)
        modo_edicion = True
        if request.method == "POST" and request.POST.get("es_edicion") == "1":
            form = ClaseForm(request.POST, instance=clase, user=selected_profesor)
            form.fields['profesor'].initial = selected_profesor.id
            if form.is_valid():
                clase_editada = form.save(commit=False)
                clase_editada.profesor = selected_profesor
                try:
                    clase_editada.save()
                    messages.success(request, "Clase editada correctamente.")
                except Exception as e:
                    messages.error(request, f"ERROR AL GUARDAR LA CLASE: {e}")
                return redirect(f"{reverse('gestionar_clases')}?profesor={selected_profesor.id}")
        else:
            initial = {
                'carrera': clase.seccion.asignatura.carrera,
                'asignatura': clase.seccion.asignatura,
                'seccion': clase.seccion,
            }
            form = ClaseForm(instance=clase, user=selected_profesor, initial=initial)
            form.fields['profesor'].initial = selected_profesor.id
    # --- CREAR ---
    elif selected_profesor:
        form = ClaseForm(request.POST or None, user=selected_profesor)
        form.fields['profesor'].initial = selected_profesor.id
        if request.method == "POST" and request.POST.get("es_edicion") == "0":
            if form.is_valid():
                nueva_clase = form.save(commit=False)
                clases_iguales = Clase.objects.filter(
                    profesor=selected_profesor,
                    dia_semana=form.cleaned_data['dia_semana'],
                    bloque_horario=form.cleaned_data['bloque_horario']
                )
                if clases_iguales.exists():
                    messages.error(request, f"Ya existe una clase para ese profesor en ese horario.")
                else:
                    nueva_clase.profesor = selected_profesor
                    try:
                        nueva_clase.save()
                        messages.success(request, "Clase agendada exitosamente.")
                    except Exception as e:
                        messages.error(request, f"ERROR AL GUARDAR LA CLASE: {e}")
                    return redirect(f"{request.path}?profesor={selected_profesor.id}")
        modo_edicion = False

    # --- MATRIZ PARA TABLERO SEMANAL ---
    matriz = {dia: {bloque.id: None for bloque in bloques} for dia in dias}
    clases = []
    clase_estudiantes = {}
    if selected_profesor:
        clases = Clase.objects.filter(
            profesor=selected_profesor,
        ).select_related('bloque_horario', 'seccion', 'seccion__asignatura', 'aula')
        for clase in clases:
            matriz[clase.dia_semana][clase.bloque_horario.id] = clase
            # Aquí calculamos la cantidad REAL de estudiantes
            num_estudiantes = EstudianteAsignaturaSeccion.objects.filter(
                seccion=clase.seccion,
                asignatura=clase.seccion.asignatura
            ).count()
            clase_estudiantes[clase.id] = num_estudiantes

    context = {
        'profesores': profesores,
        'bloques': bloques,
        'dias': dias,
        'dias_nombres': dias_nombres,
        'matriz': matriz,
        'selected_profesor_id': int(selected_profesor_id) if selected_profesor_id else None,
        'form': form,
        'modo_edicion': modo_edicion,
        'editar_id': int(editar_id) if editar_id else None,
        'clases': clases,
        'clase_estudiantes': clase_estudiantes,  # <-- esto es clave
    }
    return render(request, "clases/gestionar_clases.html", context)





























# AJAX:
from django.views.decorators.http import require_GET

@login_required
@require_GET
def get_asignaturas_ajax(request):
    carrera_id = request.GET.get('carrera_id')
    data = []
    if carrera_id:
        data = [{'id': a.id, 'nombre': a.nombre} for a in Asignatura.objects.filter(carrera_id=carrera_id)]
    return JsonResponse(data, safe=False)

@login_required
@require_GET
def get_secciones_ajax(request):
    asignatura_id = request.GET.get('asignatura_id')
    data = []
    if asignatura_id:
        data = [{'id': s.id, 'nombre': s.nombre} for s in Seccion.objects.filter(asignatura_id=asignatura_id)]
    return JsonResponse(data, safe=False)

##############################################
# DASHBOARD PROFESOR
##############################################








@login_required
def dashboard_profesor(request):
    user = request.user
    if user.user_type != 'profesor':
        return redirect('dashboard_profesor')

    # Obtener clases del semestre actual
    clases = Clase.objects.filter(
        profesor=user
    ).select_related('seccion', 'seccion__asignatura', 'bloque_horario', 'aula')

    total_clases = clases.count()
    finalizadas = clases.filter(finalizada=True).count()
    activas = clases.filter(finalizada=False).count()

    # MÉTRICAS DE ASISTENCIA
    total_asistencias = AsistenciaClase.objects.filter(clase__profesor=user).count()
    total_presentes = AsistenciaClase.objects.filter(clase__profesor=user, presente=True).count()
    total_ausentes = AsistenciaClase.objects.filter(clase__profesor=user, presente=False).count()

    # GRÁFICO SEMANAL (últimas 6 semanas)
    hoy = timezone.now().date()
    semanas = []
    datos_presentes = []
    datos_ausentes = []
    for i in range(6):
        inicio_sem = hoy - timedelta(days=hoy.weekday() + 7*i)
        fin_sem = inicio_sem + timedelta(days=6)
        week_label = f"Semana {6-i}"
        semana_asistencias = AsistenciaClase.objects.filter(
            clase__profesor=user,
            clase__fecha__range=(inicio_sem, fin_sem)
        )
        presentes = semana_asistencias.filter(presente=True).count()
        ausentes = semana_asistencias.filter(presente=False).count()
        semanas.insert(0, week_label)
        datos_presentes.insert(0, presentes)
        datos_ausentes.insert(0, ausentes)

    # Últimas 10 clases (puedes mejorar paginando, filtrando por semana, etc.)
    clases_historial = clases.order_by('-fecha')[:10]

    context = {
        'total_clases': total_clases,
        'finalizadas': finalizadas,
        'activas': activas,
        'total_asistencias': total_asistencias,
        'total_presentes': total_presentes,
        'total_ausentes': total_ausentes,
        'semanas': semanas,
        'datos_presentes': datos_presentes,
        'datos_ausentes': datos_ausentes,
        'clases_historial': clases_historial,
    }
    return render(request, "clases/dashboard_profesor.html", context)







##############################################
# AJAX ENDPOINTS
##############################################
@login_required
@require_GET
def get_asignaturas_ajax(request):
    carrera_id = request.GET.get('carrera_id')
    data = []
    if carrera_id:
        data = [{'id': a.id, 'nombre': a.nombre} for a in Asignatura.objects.filter(carrera_id=carrera_id)]
    return JsonResponse(data, safe=False)

@login_required
@require_GET
def get_secciones_ajax(request):
    asignatura_id = request.GET.get('asignatura_id')
    data = []
    if asignatura_id:
        data = [{'id': s.id, 'nombre': s.nombre} for s in Seccion.objects.filter(asignatura_id=asignatura_id)]
    return JsonResponse(data, safe=False)

##############################################
# DETALLE DE CLASE Y ASISTENCIA
##############################################
@login_required
def detalle_clase(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    estudiantes_ids = EstudianteAsignaturaSeccion.objects.filter(
        seccion=clase.seccion
    ).values_list("estudiante_id", flat=True)
    estudiantes = CustomUser.objects.filter(id__in=estudiantes_ids, user_type='estudiante')
    asistencias = {a.estudiante_id: a for a in AsistenciaClase.objects.filter(clase=clase)}
    return render(request, 'clases/detalle_clase.html', {
        'clase': clase,
        'estudiantes': estudiantes,
        'asistencias': asistencias,
    })

@csrf_exempt
@login_required
def ajax_asistencia_facial_live(request, clase_id):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"})
    data = json.loads(request.body)
    frame = data.get("frame")
    if not frame:
        return JsonResponse({"ok": False, "error": "No hay frame"})
    img_data = frame.split(",")[1]
    img_bytes = base64.b64decode(img_data)
    files = {"file": ("frame.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    try:
        response = requests.post(ARCFACE_URL, files=files, timeout=10)
        result = response.json()
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

    clase = get_object_or_404(Clase, id=clase_id)
    estudiantes_ids = EstudianteAsignaturaSeccion.objects.filter(
        seccion=clase.seccion
    ).values_list("estudiante_id", flat=True)
    estudiantes = CustomUser.objects.filter(id__in=estudiantes_ids, user_type='estudiante')

    presentes_ids = set()
    if result.get("ok"):
        for face in result["results"]:
            est_id = face.get("estudiante_id")
            if est_id:
                presentes_ids.add(est_id)
    # GUARDADO SEGURO DE ASISTENCIAS (NO SOBREESCRIBE MANUAL)
    for est in estudiantes:
        presente = est.id in presentes_ids
        asistencia, created = AsistenciaClase.objects.get_or_create(
            clase=clase, estudiante=est,
            defaults={'presente': presente, 'manual': False}
        )
        if not asistencia.manual:
            asistencia.presente = presente
            asistencia.save()
    resp_estudiantes = []
    for est in estudiantes:
        resp_estudiantes.append({
            "id": est.id,
            "nombre": est.get_full_name(),
            "presente": est.id in presentes_ids,
        })
    return JsonResponse({"ok": True, "estudiantes": resp_estudiantes})

@csrf_exempt
@login_required
def ajax_asistencia_manual(request, clase_id):
    if request.method == "POST":
        data = json.loads(request.body)
        est_id = int(data.get('estudiante_id'))
        presente = data.get('presente') == True
        estudiante = get_object_or_404(CustomUser, id=est_id, user_type='estudiante')
        asistencia, _ = AsistenciaClase.objects.get_or_create(clase_id=clase_id, estudiante=estudiante)
        asistencia.presente = presente
        asistencia.manual = True
        asistencia.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'msg': 'Método no permitido'})

@login_required
def finalizar_clase(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id, profesor=request.user)
    if request.method == "POST" and not clase.finalizada:
        clase.finalizada = True
        clase.fecha_finalizacion = timezone.now()
        clase.save()
        messages.success(request, "Clase finalizada y reporte generado.")
    return redirect("reporte_clase", clase_id=clase.id)

@login_required
def reporte_clase(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    estudiantes_ids = EstudianteAsignaturaSeccion.objects.filter(
        seccion=clase.seccion
    ).values_list("estudiante_id", flat=True)
    estudiantes = CustomUser.objects.filter(id__in=estudiantes_ids, user_type='estudiante')
    asistencias = {a.estudiante_id: a for a in AsistenciaClase.objects.filter(clase=clase)}
    total = estudiantes.count()
    presentes = sum(1 for est in estudiantes if asistencias.get(est.id) and asistencias.get(est.id).presente)
    ausentes = total - presentes
    porcentaje = (presentes / total) * 100 if total else 0

    # DEBUGGING: Verifica los valores antes de pasar al template
    for est in estudiantes:
        asis = asistencias.get(est.id)
        print(f"Est: {est.id} - {est.get_full_name()} - presente={asis.presente if asis else None} manual={asis.manual if asis else None}")

    return render(request, "clases/reporte_clase.html", {
        "clase": clase,
        "estudiantes": estudiantes,
        "asistencias": asistencias,
        "total": total,
        "presentes": presentes,
        "ausentes": ausentes,
        "porcentaje": porcentaje,
    })

###############################################








@login_required
def historial_clases(request):
    user = request.user
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    qs = Clase.objects.filter(profesor=user, finalizada=True).select_related(
        'seccion', 'seccion__asignatura', 'aula', 'bloque_horario'
    ).prefetch_related('asistencias')

    if fecha_inicio:
        qs = qs.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha__lte=fecha_fin)

    total_clases = qs.count()
    total_asistencias = AsistenciaClase.objects.filter(clase__in=qs, presente=True).count()
    total_estudiantes = AsistenciaClase.objects.filter(clase__in=qs).values('estudiante').distinct().count()

    # Gráfico semanal (6 semanas)
    from django.utils import timezone
    resumen_semanal = []
    hoy = timezone.now().date()
    for i in range(6, 0, -1):
        inicio = hoy - timezone.timedelta(days=7*i)
        fin = hoy - timezone.timedelta(days=7*(i-1))
        semana_clases = qs.filter(fecha__range=[inicio, fin])
        semana_asist = AsistenciaClase.objects.filter(clase__in=semana_clases, presente=True).count()
        resumen_semanal.append({
            'semana': f"{inicio.strftime('%d/%m')} - {fin.strftime('%d/%m')}",
            'clases': semana_clases.count(),
            'asistencias': semana_asist,
        })

    detalle = []
    for clase in qs.order_by('-fecha'):
        presentes = clase.asistencias.filter(presente=True).count()
        total = clase.asistencias.count()
        detalle.append({
            'clase': clase,
            'presentes': presentes,
            'total': total,
            'porcentaje': (presentes/total*100) if total else 0,
        })

    context = {
        'total_clases': total_clases,
        'total_asistencias': total_asistencias,
        'total_estudiantes': total_estudiantes,
        'resumen_semanal': resumen_semanal,
        'detalle': detalle,
        'fecha_inicio': fecha_inicio or '',
        'fecha_fin': fecha_fin or '',
    }
    return render(request, 'clases/historial_clases.html', context)












###############################################
################################################
# HORARIO DEL PROFESOR
################################################

@login_required
def horario_profesor(request):
    user = request.user
    if user.user_type != 'profesor':
        return redirect('dashboard_profesor')
    semanas = SemanaAcademica.objects.filter(calendario__sede=user.sede).order_by('numero')
    semana_id = request.GET.get('semana')
    if semana_id:
        semana_seleccionada = semanas.filter(id=semana_id).first()
    else:
        semana_seleccionada = semanas.filter(tipo='clases').order_by('fecha_inicio').first()
    bloques = BloqueHorario.objects.order_by('hora_inicio')
    dias = ['LU', 'MA', 'MI', 'JU', 'VI', 'SA']
    matriz = {dia: {bloque.id: None for bloque in bloques} for dia in dias}
    if semana_seleccionada:
        clases = Clase.objects.filter(
            profesor=user,
            semana_academica=semana_seleccionada
        ).select_related('bloque_horario', 'seccion', 'seccion__asignatura', 'aula')
        for clase in clases:
            matriz[clase.dia_semana][clase.bloque_horario.id] = clase
    context = {
        'semanas': semanas,
        'semana_seleccionada': semana_seleccionada,
        'bloques': bloques,
        'dias': dias,
        'matriz': matriz,
    }
    return render(request, "clases/horario_profesor.html", context)