from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from django.forms import HiddenInput
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models     import Count
from core.decorators import admin_zona_required, admin_global_required, profesor_required
from core.models import CustomUser, SemanaAcademica
from django.http import JsonResponse, HttpResponseBadRequest

from django.middleware.csrf import get_token



from sedes.models import Sede, Carrera, Asignatura, Seccion
from personas.models import EstudianteAsignaturaSeccion, EstudianteAsignaturaSeccion

from .models import (
    BloqueHorario,
    Aula,
    Clase,
    ClasePlantillaVersion,
    ClaseInstancia,
    AsistenciaClase,
)
from .forms import BloqueHorarioForm, AulaForm, ClaseForm

from collections import defaultdict
import io, json, base64, requests
from datetime import timedelta
from django.conf import settings
from django.db import transaction
# ========== CONFIGURACIÓN ARC FACE ==========
ARCFACE_URL = "http://localhost:8001/match_faces/"





# Después de todos tus imports, añade:
DIAS_SEMANA = [
    ('LU', 'Lunes'),
    ('MA', 'Martes'),
    ('MI', 'Miércoles'),
    ('JU', 'Jueves'),
    ('VI', 'Viernes'),
    ('SA', 'Sábado'),
]

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
    # Obtener parámetros de edición/eliminación
    editar_id   = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    # ELIMINAR
    if eliminar_id:
        aula = get_object_or_404(Aula, id=eliminar_id, sede=request.user.sede)
        aula.delete()
        messages.success(request, "Aula eliminada correctamente.")
        return redirect("gestionar_aulas")

    # EDITAR: cargar instancia en el form
    if editar_id:
        instancia = get_object_or_404(Aula, id=editar_id, sede=request.user.sede)
        form = AulaForm(request.POST or None, instance=instancia)
    else:
        # CREAR: form vacío con valor inicial camara_ip="0"
        form = AulaForm(request.POST or None)

    # PROCESAR FORM
    if request.method == 'POST' and form.is_valid():
        aula = form.save(commit=False)
        aula.sede = request.user.sede
        # Si el usuario dejó camara_ip vacío, forzar "0"
        if not aula.camara_ip:
            aula.camara_ip = "0"
        aula.save()
        accion = "Actualizada" if editar_id else "Creada"
        messages.success(request, f"Aula {accion} correctamente.")
        return redirect("gestionar_aulas")

    # LISTADO: solo aulas de la sede del usuario
    aulas = Aula.objects.filter(sede=request.user.sede).order_by('numero_sala')

    return render(request, 'clases/gestionar_aulas.html', {
        'form':      form,
        'aulas':     aulas,
        'editar_id': editar_id,
    })

##############################################
# CRUD CLASES — VISUAL / TABLERO SEMANAL
##############################################




@login_required
@admin_zona_required
def gestionar_clases(request):
    user = request.user

    # 1) Profesores y selección
    profesores = CustomUser.objects.filter(user_type='profesor', sede=user.sede).order_by('last_name')
    prof_id = request.GET.get('profesor')
    selected_profesor = get_object_or_404(profesores, pk=prof_id) if prof_id else None

    # 2) Semanas y estado publicado
    semanas = list(SemanaAcademica.objects.filter(calendario__sede=user.sede).order_by('numero'))
    any_publicada = selected_profesor and Clase.objects.filter(profesor=selected_profesor, publicada=True).exists()
    sem_act = None
    if any_publicada and semanas:
        sid = request.GET.get('semana') or semanas[0].id
        sem_act = get_object_or_404(SemanaAcademica, pk=sid)

    # 3) Crear nueva plantilla + generar instancias
    form = ClaseForm(request.POST or None, user=user) if selected_profesor else None
    if selected_profesor and request.method=='POST' and 'agregar' in request.POST:
        if form.is_valid():
            nueva = form.save(commit=False)
            nueva.profesor = selected_profesor
            nueva.save()
            if semanas:
                version = ClasePlantillaVersion.objects.create(
                    plantilla=nueva,
                    effective_from=semanas[0]
                )
                for sem in semanas:
                    ClaseInstancia.objects.update_or_create(
                        version=version,
                        semana_academica=sem,
                        defaults={'fecha': sem.fecha_inicio + nueva.get_dia_semana_delta()}
                    )
            messages.success(request, "Plantilla creada y aplicada a todo el semestre.")
            return redirect(f"{reverse('gestionar_clases')}?profesor={selected_profesor.id}")
        messages.error(request, "Corrige los errores del formulario.")

    # 4) Publicar semestre
    if selected_profesor and request.method=='POST' and 'publicar' in request.POST:
        if semanas:
            for pl in Clase.objects.filter(profesor=selected_profesor, publicada=False):
                ver, _ = ClasePlantillaVersion.objects.get_or_create(plantilla=pl, effective_from=semanas[0])
                for sem in semanas:
                    ClaseInstancia.objects.update_or_create(
                        version=ver,
                        semana_academica=sem,
                        defaults={'fecha': sem.fecha_inicio + pl.get_dia_semana_delta()}
                    )
                pl.publicada = True
                pl.save()
            messages.success(request, "Todas las plantillas publicadas.")
        else:
            messages.warning(request, "No hay semanas académicas definidas.")
        return redirect(f"{reverse('gestionar_clases')}?profesor={selected_profesor.id}")

    # 5) Editar / Eliminar con alcance
    if selected_profesor and request.method=='POST' and request.POST.get('action') in (
        'editar_plantilla','eliminar_plantilla','eliminar_inst'
    ):
        action = request.POST['action']
        target = int(request.POST['target_id'])
        scope  = request.POST.get('scope')

        # EDITAR PLANTILLA
        if action=='editar_plantilla':
            nueva_seccion = get_object_or_404(Seccion, pk=request.POST['seccion'])
            nueva_aula    = get_object_or_404(Aula, pk=request.POST['aula'])

            if any_publicada and scope=='week':
                pl_orig = get_object_or_404(Clase, pk=target, profesor=selected_profesor)
                inst = get_object_or_404(
                    ClaseInstancia,
                    version__plantilla=pl_orig,
                    semana_academica=sem_act
                )
                clone = Clase.objects.create(
                    profesor        = pl_orig.profesor,
                    seccion         = nueva_seccion,
                    aula            = nueva_aula,
                    dia_semana      = pl_orig.dia_semana,
                    bloque_horario  = pl_orig.bloque_horario,
                    publicada       = True
                )
                ver_clone = ClasePlantillaVersion.objects.create(plantilla=clone, effective_from=sem_act)
                inst.version = ver_clone
                inst.save()
            else:
                pl = get_object_or_404(Clase, pk=target, profesor=selected_profesor)
                if any_publicada and scope!='week':
                    ver, _ = ClasePlantillaVersion.objects.get_or_create(plantilla=pl, effective_from=sem_act)
                    pl.seccion = nueva_seccion
                    pl.aula    = nueva_aula
                    pl.save()
                    for sem in semanas:
                        if sem.numero >= sem_act.numero:
                            ClaseInstancia.objects.update_or_create(
                                version=ver,
                                semana_academica=sem,
                                defaults={'fecha': sem.fecha_inicio + pl.get_dia_semana_delta()}
                            )
                else:
                    pl.seccion = nueva_seccion
                    pl.aula    = nueva_aula
                    pl.save()
            messages.success(request, "Plantilla editada correctamente.")

        # ELIMINAR INSTANCIA
        elif action=='eliminar_inst':
            if scope=='week':
                ClaseInstancia.objects.filter(pk=target).delete()
            else:
                inst = get_object_or_404(
                    ClaseInstancia,
                    pk=target,
                    version__plantilla__profesor=selected_profesor
                )
                for sem in semanas:
                    if sem.numero >= sem_act.numero:
                        ClaseInstancia.objects.filter(
                            version=inst.version,
                            semana_academica=sem
                        ).delete()
            messages.success(request, "Instancia eliminada correctamente.")

        # ELIMINAR PLANTILLA
        else:
            if any_publicada and scope=='week':
                ver = get_object_or_404(
                    ClasePlantillaVersion,
                    plantilla__pk=target,
                    effective_from=sem_act
                )
                ClaseInstancia.objects.filter(version=ver, semana_academica=sem_act).delete()
            else:
                versiones = ClasePlantillaVersion.objects.filter(
                    plantilla__profesor=selected_profesor,
                    effective_from__gte=sem_act
                )
                for ver in versiones:
                    ver.instancias.filter(semana_academica__numero__gte=sem_act.numero).delete()
                    ver.delete()
            messages.success(request, "Plantilla eliminada correctamente.")

        return redirect(f"{reverse('gestionar_clases')}?profesor={selected_profesor.id}&semana={sem_act.id}")

    # 6) Construir matriz
    bloques      = BloqueHorario.objects.order_by('hora_inicio')
    dias         = [d for d,_ in DIAS_SEMANA]
    dias_nombres = [n for _,n in DIAS_SEMANA]
    matriz       = {d:{b.id: None for b in bloques} for d in dias}

    instancias = []
    if selected_profesor and any_publicada:
        instancias = ClaseInstancia.objects.filter(
            version__plantilla__profesor=selected_profesor,
            semana_academica=sem_act
        ).select_related(
            'version__plantilla__bloque_horario',
            'version__plantilla__seccion',
            'version__plantilla__aula'
        )
        for inst in instancias:
            pl = inst.version.plantilla
            matriz[pl.dia_semana][pl.bloque_horario.id] = inst

    # 7) Contar estudiantes por sección
    section_ids = {inst.version.plantilla.seccion.id for inst in instancias}
    qs_counts = (
        EstudianteAsignaturaSeccion.objects
        .filter(seccion_id__in=section_ids)
        .values('seccion_id')
        .annotate(cnt=Count('id'))
    )
    counts_map = {entry['seccion_id']: entry['cnt'] for entry in qs_counts}

    return render(request, 'clases/gestionar_clases.html', {
        'profesores':        profesores,
        'selected_profesor':  selected_profesor,
        'semanas':           semanas,
        'sem_act':           sem_act,
        'any_publicada':     any_publicada,
        'form':              form,
        'bloques':           bloques,
        'dias':              dias,
        'dias_nombres':      dias_nombres,
        'matriz':            matriz,
        'counts_map':        counts_map,
    })





      

# Endpoints AJAX para poblar selectores
@require_GET
@login_required
@admin_zona_required
def get_asignaturas_ajax(request):
    qs = Asignatura.objects.filter(carrera__sede=request.user.sede).values('id','nombre')
    return JsonResponse(list(qs), safe=False)

@require_GET
@login_required
@admin_zona_required
def get_secciones_ajax(request):
    aid = request.GET.get('asignatura_id')
    qs = Seccion.objects.filter(asignatura_id=aid).values('id','nombre')
    return JsonResponse(list(qs), safe=False)




@login_required
@profesor_required
def horario_profesor(request):
    user = request.user

    # 1) Semanas de la sede del profesor
    semanas = (SemanaAcademica.objects
               .filter(calendario__sede=user.sede)
               .order_by('numero'))
    semana_id = request.GET.get('semana')
    if semana_id:
        sem_sel = get_object_or_404(semanas, pk=semana_id)
    else:
        sem_sel = semanas.first()

    # 2) Bloques y días
    bloques      = BloqueHorario.objects.order_by('hora_inicio')
    dias_codes   = [code for code, _ in DIAS_SEMANA]
    dias_nombres = [name for _, name in DIAS_SEMANA]

    # 3) Instancias de clase del profesor en la semana seleccionada
    instancias = (ClaseInstancia.objects
                  .filter(version__plantilla__profesor=user,
                          semana_academica=sem_sel)
                  .select_related(
                      'version__plantilla__bloque_horario',
                      'version__plantilla__seccion',
                      'version__plantilla__aula'
                  ))

    # 4) Construir la matriz[dia][bloque_id] = instancia
    matriz = {dia: {b.id: None for b in bloques} for dia in dias_codes}
    for inst in instancias:
        dia   = inst.version.plantilla.dia_semana
        bid   = inst.version.plantilla.bloque_horario.id
        matriz[dia][bid] = inst

    # 5) Contar estudiantes por sección (misma lógica que en gestionar_clases)
    section_ids = {
        inst.version.plantilla.seccion.id
        for inst in instancias
    }
    qs_counts = (
        EstudianteAsignaturaSeccion.objects
        .filter(seccion_id__in=section_ids)
        .values('seccion_id')
        .annotate(cnt=Count('id'))
    )
    counts_map = {entry['seccion_id']: entry['cnt'] for entry in qs_counts}

    return render(request, 'clases/horario_profesor.html', {
        'semanas':      semanas,
        'semana_sel':   sem_sel,
        'bloques':      bloques,
        'dias':         dias_codes,
        'dias_nombres': dias_nombres,
        'matriz':       matriz,
        'counts_map':   counts_map,
    })
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


##############################################
# DETALLE DE CLASE Y ASISTENCIA
##############################################


@login_required
def detalle_instancia(request, inst_id):
    # 1) instancia de clase
    instancia = get_object_or_404(ClaseInstancia, id=inst_id)
    plantilla = instancia.version.plantilla

    # 2) estudiantes inscritos
    estudiantes_ids = EstudianteAsignaturaSeccion.objects.filter(
        seccion=plantilla.seccion
    ).values_list("estudiante_id", flat=True)
    estudiantes = CustomUser.objects.filter(
        id__in=estudiantes_ids, user_type='estudiante'
    )

    # 3) asistencias previas
    asistencias_qs = AsistenciaClase.objects.filter(instancia=instancia)
    asistencias = { a.estudiante_id: a.presente for a in asistencias_qs }

    # 4) URLs para AJAX
    match_url  = settings.ARC_FACE_URL.rstrip('/') + '/match/'
    manual_url = reverse('clases:ajax_asistencia_manual', args=[instancia.id])

    return render(request, 'clases/detalle_instancia.html', {
        'instancia':   instancia,
        'estudiantes': estudiantes,
        'asistencias': asistencias,
        'match_url':   match_url,
        'manual_url':  manual_url,
    })


@require_POST
def ajax_match_face(request):
    img = request.FILES.get('file')
    if not img:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    files = {'file': (img.name, img.read(), img.content_type)}
    try:
        resp = requests.post(
            f"{settings.ARC_FACE_URL.rstrip('/')}/match/",
            files=files,
            timeout=5
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return JsonResponse({'error': str(e)}, status=502)

    data = resp.json()  # { matched: True/False }
    return JsonResponse({
        'ok': True,
        'results': [{
            'match': data.get('matched', False),
            'estudiante_id': int(request.POST.get('est_id', 0))  # si lo envías desde JS
        }]
    })

















###################################################################
###################################################################
###################################################################
###################################################################


@require_POST
def ajax_asistencia_facial_live(request, inst_id):
    """
    Recibe un JSON { frame: dataURL }, reenvía a /match_faces/ y devuelve:
      { ok, estudiantes: [ { id, presente }, ... ] }
    """
    instancia = get_object_or_404(ClaseInstancia, pk=inst_id)
    try:
        payload = json.loads(request.body)
        data_url = payload.get('frame')
        if not data_url:
            return HttpResponseBadRequest("No viene frame")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON inválido")

    # Enviar al microservicio ArcFace
    resp = requests.post(
        settings.ARCFACE_SERVICE_URL + '/match_faces/',
        files={'file': data_url.split(',',1)[1]},
        timeout=5
    )
    if resp.status_code != 200:
        return JsonResponse({
            'ok': False,
            'error': f"Servicio ArcFace devolvió {resp.status_code}"
        }, status=500)

    try:
        result = resp.json()
    except ValueError:
        return JsonResponse({
            'ok': False,
            'error': 'Respuesta no JSON de ArcFace'
        }, status=500)

    if not result.get('ok'):
        return JsonResponse({ 'ok': False, 'msg': result.get('msg','Error') })

    # Mapear resultados: marca o desmarca asistencia
    salida = []
    for r in result['results']:
        eid = r.get('estudiante_id')
        pres = r.get('match', False)
        if eid:
            obj, _ = AsistenciaClase.objects.update_or_create(
                instancia=instancia,
                estudiante_id=eid,
                defaults={'presente': pres, 'manual': False}
            )
        salida.append({'id': eid, 'presente': pres})

    return JsonResponse({'ok': True, 'estudiantes': salida})


@require_POST
def ajax_asistencia_manual(request, inst_id):
    """
    Recibe JSON { estudiante_id, presente } y guarda la AsistenciaClase.
    """
    instancia = get_object_or_404(ClaseInstancia, pk=inst_id)
    try:
        payload = json.loads(request.body)
        eid = payload['estudiante_id']
        pres = bool(payload['presente'])
    except (ValueError, KeyError):
        return HttpResponseBadRequest("JSON inválido")

    AsistenciaClase.objects.update_or_create(
        instancia=instancia,
        estudiante_id=eid,
        defaults={'presente': pres, 'manual': True}
    )
    return JsonResponse({'ok': True})









@login_required
@require_GET
def get_secciones_ajax(request):
    """
    Devuelve JSON con las secciones de una asignatura dada.
    Parámetro GET: ?asignatura_id=<id>
    """
    asignatura_id = request.GET.get('asignatura_id')
    if not asignatura_id:
        return JsonResponse({'error': 'Falta asignatura_id'}, status=400)

    secciones = Seccion.objects.filter(asignatura_id=asignatura_id).values('id', 'nombre')
    # output: [ {'id':1,'nombre':'001A'}, ... ]
    return JsonResponse(list(secciones), safe=False)






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

























