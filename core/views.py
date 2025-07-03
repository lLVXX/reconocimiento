# CORE/VIEWS.PY
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from clases.models import AsistenciaClase, ClaseInstancia
from datetime import timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, F
import io
import pandas as pd
from xhtml2pdf import pisa

from django.template.loader  import render_to_string

# Formularios propios
from .forms import CalendarioGlobalForm, EditarCalendarioForm, EditarSemanaForm
from .forms import CustomLoginForm, AdminZonaForm, CalendarioWizardForm
from personas.forms import EstudianteForm
from .models import CalendarioAcademico, SemanaAcademica, Sede
# Modelos propios
from .models import CustomUser
from sedes.models import Seccion
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.utils import timezone


from sedes.models import Sede, Carrera, Asignatura, Seccion
from core.models import CustomUser
from clases.models import Clase, AsistenciaClase
from personas.models import EstudianteAsignaturaSeccion


# Decoradores y utilidades personalizadas
from core.decorators import admin_zona_required
from core.decorators import admin_global_required

@login_required
def redirigir_por_rol(request):
    user = request.user
    if user.is_superuser:
        return redirect('/admin/')  # panel normal de Django
    elif user.user_type == 'admin_global':
        return redirect('dashboard_admin_global')
    elif user.user_type == 'admin_zona':
        return redirect('dashboard_admin_zona')
    else:
        return redirect('logout')


def is_admin_zona(user):
    return user.is_authenticated and user.user_type == 'admin_zona'




def portal_inicio(request):
    if request.method == "POST":
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            if user.user_type == 'admin_global':
                return redirect('dashboard_admin_global')
            # puedes agregar más redirecciones aquí
    else:
        form = CustomLoginForm()
    return render(request, 'core/portal_inicio.html', {'form': form})





























@login_required
@admin_global_required
def dashboard_admin_global(request):
    # 1) Sedes y filtro
    sedes    = Sede.objects.order_by('nombre')
    sede_id  = request.GET.get('sede', 'all')
    sede_sel = None if sede_id == 'all' else sedes.filter(id=sede_id).first()

    # 2) Filtro para instancias
    filtro_inst = {} if not sede_sel else {
        'version__plantilla__profesor__sede': sede_sel
    }

    # 3) Totales generales
    total_sedes       = sedes.count()
    carreras_qs       = Carrera.objects.filter(sede=sede_sel) if sede_sel else Carrera.objects.all()
    total_carreras    = carreras_qs.count()
    asignaturas_qs    = Asignatura.objects.filter(carrera__in=carreras_qs)
    total_asignaturas = asignaturas_qs.count()
    estudiantes_qs    = CustomUser.objects.filter(user_type='estudiante', sede=sede_sel) if sede_sel else CustomUser.objects.filter(user_type='estudiante')
    total_estudiantes = estudiantes_qs.count()
    clases_qs         = ClaseInstancia.objects.filter(finalizada=True, **filtro_inst)
    total_clases      = clases_qs.count()
    regs_qs           = AsistenciaClase.objects.filter(instancia__in=clases_qs)
    total_regs        = regs_qs.count()
    pres_qs           = regs_qs.filter(presente=True).count()
    pct_global        = round(pres_qs * 100.0 / total_regs, 2) if total_regs else 0.00

    # 4) Métricas por carrera (incluye nombre de sede si "todas")
    carreras_stats = []
    for c in carreras_qs:
        insts = clases_qs.filter(version__plantilla__seccion__asignatura__carrera=c)
        regs  = AsistenciaClase.objects.filter(instancia__in=insts)
        cnt_cl = insts.count()
        cnt_rg = regs.count()
        cnt_pr = regs.filter(presente=True).count()
        pct    = round(cnt_pr * 100.0 / cnt_rg, 2) if cnt_rg else 0.00
        carreras_stats.append({
            'nombre':     c.nombre,
            'sede':       None if sede_sel else c.sede.nombre,
            'clases':     cnt_cl,
            'porcentaje': pct,
        })

    # 5) Métricas por asignatura (incluye nombre de sede si "todas")
    asignaturas_stats = []
    for a in asignaturas_qs:
        insts = clases_qs.filter(version__plantilla__seccion__asignatura=a)
        regs  = AsistenciaClase.objects.filter(instancia__in=insts)
        cnt_cl = insts.count()
        cnt_rg = regs.count()
        cnt_pr = regs.filter(presente=True).count()
        pct    = round(cnt_pr * 100.0 / cnt_rg, 2) if cnt_rg else 0.00
        asignaturas_stats.append({
            'nombre':     a.nombre,
            'sede':       None if sede_sel else a.carrera.sede.nombre,
            'clases':     cnt_cl,
            'porcentaje': pct,
        })

    # 6) Estudiantes por carrera
    estudiantes_stats = []
    for c in carreras_qs:
        alumnos = EstudianteAsignaturaSeccion.objects.filter(
            asignatura__carrera=c
        ).values('estudiante').distinct().count()
        estudiantes_stats.append({
            'nombre': c.nombre,
            'alumnos': alumnos,
        })

    # 7) Exportar PDF completo
    if request.GET.get('format') == 'pdf':
        sedes_data = []
        for sede in (sedes if not sede_sel else [sede_sel]):
            sd = {'nombre': sede.nombre, 'carreras': []}
            for c in Carrera.objects.filter(sede=sede):
                cd = {'nombre': c.nombre, 'secciones': []}
                for sec in Seccion.objects.filter(asignatura__carrera=c).distinct():
                    # cada sección apunta a una única asignatura
                    a = sec.asignatura
                    insts = ClaseInstancia.objects.filter(
                        finalizada=True,
                        version__plantilla__profesor__sede=sede,
                        version__plantilla__seccion=sec
                    )
                    regs = AsistenciaClase.objects.filter(instancia__in=insts)
                    total_i = regs.count()
                    pres_i  = regs.filter(presente=True).count()
                    man_i   = regs.filter(presente=True, manual=True).count()
                    auto_i  = pres_i - man_i
                    pct_i   = round(pres_i * 100.0 / total_i, 2) if total_i else 0.00
                    cd['secciones'].append({
                        'sec_nombre':    sec.nombre,
                        'asig_nombre':   a.nombre,
                        'sede':          None if sede_sel else sede.nombre,
                        'total_clases':  insts.count(),
                        'manual':        man_i,
                        'automatico':    auto_i,
                        'porcentaje':    pct_i,
                    })
                sd['carreras'].append(cd)
            sedes_data.append(sd)

        context = {
            'sede_sel':   sede_sel.nombre if sede_sel else 'Todas las sedes',
            'sedes_data': sedes_data,
        }
        return export_to_pdf(
            'exports/pdf_admin_global_full.html',
            context,
            filename=f"dashboard_global_{sede_sel.nombre if sede_sel else 'all'}"
        )

    # 8) Renderizar HTML
    return render(request, 'core/dashboard_admin_global.html', {
        'sedes':               sedes,
        'sede_sel':            sede_sel,
        'total_sedes':         total_sedes,
        'total_carreras':      total_carreras,
        'total_asignaturas':   total_asignaturas,
        'total_estudiantes':   total_estudiantes,
        'total_clases':        total_clases,
        'pct_global':          pct_global,
        'carreras_stats':      carreras_stats,
        'asignaturas_stats':   asignaturas_stats,
        'estudiantes_stats':   estudiantes_stats,
    })








def cerrar_sesion(request):
    logout(request)
    return redirect('portal_inicio')



##################################################}


@login_required
@admin_global_required
def gestionar_admin_zona(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    # Eliminar usuario
    if eliminar_id:
        usuario = get_object_or_404(CustomUser, id=eliminar_id, user_type='admin_zona')
        usuario.delete()
        messages.success(request, "Administrador de zona eliminado correctamente.")
        return redirect("gestionar_admin_zona")

    # Editar usuario
    if editar_id:
        instance = get_object_or_404(CustomUser, id=editar_id, user_type='admin_zona')
        form = AdminZonaForm(request.POST or None, instance=instance)
    else:
        form = AdminZonaForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            nombre = form.cleaned_data['nombre']
            apellido = form.cleaned_data['apellido']
            rut = form.cleaned_data['rut']
            sede = form.cleaned_data['sede']

            nombre_corto = nombre[:2].lower()
            apellido_lower = apellido.lower()
            sede_nombre = sede.nombre.lower().replace(" ", "")
            email_generado = f"{nombre_corto}.{apellido_lower}@{sede_nombre}.com"
            username_base = f"{nombre_corto}{apellido_lower}"

            # Evitar colisiones de username/email
            username_final = username_base
            i = 1
            while CustomUser.objects.filter(username=username_final).exists():
                username_final = f"{username_base}{i}"
                i += 1

            email_final = email_generado
            i = 1
            while CustomUser.objects.filter(email=email_final).exists():
                email_final = f"{nombre_corto}.{apellido_lower}{i}@{sede_nombre}.com"
                i += 1

            instance.email = email_final
            instance.username = username_final
            instance.first_name = nombre
            instance.last_name = apellido
            instance.user_type = 'admin_zona'
            instance.workzone = sede
            instance.rut = rut

            if not editar_id:
                instance.set_password('12345678')

            instance.save()
            messages.success(request, f"{'Actualizado' if editar_id else 'Creado'} correctamente: {username_final}")
            return redirect("gestionar_admin_zona")
        else:
            messages.error(request, "Revisa los errores del formulario.")

    adminzonas = CustomUser.objects.filter(user_type='admin_zona').select_related('workzone')

    return render(request, "core/gestionar_admin_zona.html", {
        'form': form,
        'adminzonas': adminzonas,
        'editar_id': editar_id
    })

##################################################################


def export_to_excel(rows, filename):
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)
    resp = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return resp


def export_to_pdf(template_src, context, filename):
    html = render_to_string(template_src, context)
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    resp = HttpResponse(result.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    return resp


@login_required
@admin_zona_required
def dashboard_admin_zona(request):
    sede = request.user.sede
    admin_nombre = request.user.get_full_name()

    # Totales generales
    total_profesores  = CustomUser.objects.filter(user_type='profesor', sede=sede).count()
    total_estudiantes = CustomUser.objects.filter(user_type='estudiante', sede=sede).count()
    total_clases      = ClaseInstancia.objects.filter(
        finalizada=True,
        version__plantilla__profesor__sede=sede
    ).count()

    # Resumen por Profesor
    profes = CustomUser.objects.filter(user_type='profesor', sede=sede)

    # Clases dadas
    cp = (ClaseInstancia.objects
          .filter(finalizada=True, version__plantilla__profesor__in=profes)
          .values('version__plantilla__profesor')
          .annotate(dadas=Count('id')))
    clases_map = {e['version__plantilla__profesor']: e['dadas'] for e in cp}

    # Asistencia global
    ap = (AsistenciaClase.objects
          .filter(instancia__version__plantilla__profesor__in=profes)
          .values('instancia__version__plantilla__profesor')
          .annotate(
              registros=Count('id'),
              presentes=Count('id', filter=Q(presente=True))
          ))
    asist_map = {e['instancia__version__plantilla__profesor']: e for e in ap}

    # Armar stats por profesor con detalle por asignatura y sección
    prof_stats = []
    for p in profes:
        dadas = clases_map.get(p.id, 0)
        d = asist_map.get(p.id, {'registros': 0, 'presentes': 0})
        regs, pres = d['registros'], d['presentes']
        pct = round((pres * 100.0 / regs), 2) if regs else 0.00

        insts = ClaseInstancia.objects.filter(
            version__plantilla__profesor=p,
            finalizada=True
        ).select_related(
            'version__plantilla__seccion__asignatura',
            'version__plantilla__seccion'
        )

        detalle_map = {}
        for inst in insts:
            asig = inst.version.plantilla.seccion.asignatura.nombre
            secc = inst.version.plantilla.seccion.nombre
            key = (asig, secc)
            if key not in detalle_map:
                detalle_map[key] = {'manual': 0, 'auto': 0}
            for a in inst.asistencias.filter(presente=True):
                if getattr(a, 'manual', False):
                    detalle_map[key]['manual'] += 1
                else:
                    detalle_map[key]['auto'] += 1

        detalle = [
            {'asignatura': asig, 'seccion': secc, 
             'manual': cnts['manual'], 'automatico': cnts['auto']}
            for (asig, secc), cnts in detalle_map.items()
        ]

        secciones_ids = insts.values_list('version__plantilla__seccion', flat=True).distinct()
        est_count = EstudianteAsignaturaSeccion.objects.filter(
            seccion_id__in=secciones_ids
        ).values('estudiante').distinct().count()

        prof_stats.append({
            'nombre':       p.get_full_name(),
            'clases_dadas': dadas,
            'estudiantes':  est_count,
            'porcentaje':   f"{pct:.2f}",
            'detalle':      detalle,
        })

    # Exportación
    fmt = request.GET.get('format')
    if fmt in ('excel', 'pdf'):
        base_fn = f"dashboard_admin_zona_{sede.nombre}"
        if fmt == 'excel':
            rows = []
            for r in prof_stats:
                for d in r['detalle']:
                    rows.append({
                        'Administrador':  admin_nombre.title(),
                        'Profesor':       r['nombre'].title(),
                        'Asignatura':     d['asignatura'].title(),
                        'Sección':        d['seccion'].title(),
                        'Manual':         d['manual'],
                        'Automático':     d['automatico'],
                        '% Asistencia':   r['porcentaje'],
                    })
            return export_to_excel(rows, filename=base_fn)
        else:
            context = {
                'zona':              sede.nombre.title(),
                'admin_nombre':      admin_nombre.title(),
                'total_profesores':  total_profesores,
                'total_estudiantes': total_estudiantes,
                'total_clases':      total_clases,
                'prof_stats':        prof_stats,
            }
            return export_to_pdf('exports/pdf_adminzona.html', context, filename=base_fn)

    # Render normal
    return render(request, 'core/dashboard_admin_zona.html', {
        'total_profesores':  total_profesores,
        'total_estudiantes': total_estudiantes,
        'total_clases':      total_clases,
        'carreras':          Carrera.objects.filter(sede=sede),
        'selected_carrera':  None,
        'resumen_profs':     prof_stats,
    })











############################################################

@login_required
def gestionar_calendario(request):
    user = request.user
    es_admin_global = user.user_type == 'admin_global'
    es_admin_zona = user.user_type == 'admin_zona'

    # CREAR CALENDARIO - Solo admin_global
    if es_admin_global and request.method == "POST" and 'crear' in request.POST:
        form = CalendarioGlobalForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            fecha_inicio = form.cleaned_data['fecha_inicio']
            semanas = form.cleaned_data['semanas']
            fecha_fin = fecha_inicio + timedelta(weeks=semanas) - timedelta(days=1)
            sedes = Sede.objects.all()
            for sede in sedes:
                calendario = CalendarioAcademico.objects.create(
                    sede=sede,
                    nombre=nombre,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                )
                for i in range(semanas):
                    ini = fecha_inicio + timedelta(weeks=i)
                    fin = ini + timedelta(days=6)
                    SemanaAcademica.objects.create(
                        calendario=calendario,
                        numero=i + 1,
                        fecha_inicio=ini,
                        fecha_fin=fin,
                        tipo='clases'
                    )
            messages.success(request, f"Calendario '{nombre}' creado para todas las sedes.")
            return redirect('gestionar_calendario')
    else:
        form = CalendarioGlobalForm()

    # ELIMINAR CALENDARIO - Solo admin_global
    if es_admin_global and request.method == "POST" and 'eliminar' in request.POST:
        calendario_id = request.POST.get('eliminar')
        calendario = get_object_or_404(CalendarioAcademico, id=calendario_id)
        calendario.delete()
        messages.success(request, "Calendario eliminado correctamente.")
        return redirect('gestionar_calendario')

    # EDITAR SEMANAS (para ambos, según permisos)
    if request.method == "POST" and 'guardar_semanas' in request.POST:
        calendario_id = request.POST.get('calendario_id')
        calendario = get_object_or_404(CalendarioAcademico, id=calendario_id)
        if es_admin_global or (es_admin_zona and calendario.sede == user.sede):
            semanas = SemanaAcademica.objects.filter(calendario=calendario).order_by('numero')
            for semana in semanas:
                prefix = f"semana_{semana.pk}_"
                semana.numero = request.POST.get(f'{prefix}numero', semana.numero)
                semana.fecha_inicio = request.POST.get(f'{prefix}fecha_inicio', semana.fecha_inicio)
                semana.fecha_fin = request.POST.get(f'{prefix}fecha_fin', semana.fecha_fin)
                semana.tipo = request.POST.get(f'{prefix}tipo', semana.tipo)
                semana.descripcion = request.POST.get(f'{prefix}descripcion', semana.descripcion)
                semana.save()
            messages.success(request, "Semanas actualizadas correctamente.")
            return redirect('gestionar_calendario')

    # LISTADO
    if es_admin_global:
        calendarios = CalendarioAcademico.objects.select_related('sede').all().order_by('nombre', 'sede__nombre')
    elif es_admin_zona:
        calendarios = CalendarioAcademico.objects.filter(sede=user.sede).order_by('nombre')
    else:
        calendarios = []

    # Semana para editar (si existe query param ?edit=XX)
    calendario_editar = None
    semanas = []
    edit_id = request.GET.get('edit')
    if edit_id:
        calendario_editar = get_object_or_404(CalendarioAcademico, id=edit_id)
        if es_admin_global or (es_admin_zona and calendario_editar.sede == user.sede):
            semanas = SemanaAcademica.objects.filter(calendario=calendario_editar).order_by('numero')
        else:
            calendario_editar = None

    context = {
        'form': form,
        'calendarios': calendarios,
        'calendario_editar': calendario_editar,
        'semanas': semanas,
        'es_admin_global': es_admin_global,
        'es_admin_zona': es_admin_zona,
    }
    return render(request, "core/gestionar_calendario.html", context)















@login_required
@user_passes_test(admin_global_required)
def exportar_dashboard_pdf(request):
    # Copia la lógica de métricas y filtros EXACTA al dashboard_admin_global
    sede_id = request.GET.get("sede")
    carrera_id = request.GET.get("carrera")
    sede_actual = Sede.objects.filter(id=sede_id).first() if sede_id else None
    carrera_actual = Carrera.objects.filter(id=carrera_id).first() if carrera_id else None

    sedes = Sede.objects.all().order_by('nombre')
    total_sedes = sedes.count()
    total_carreras = Carrera.objects.count()
    total_asignaturas = Asignatura.objects.count()
    total_secciones = Seccion.objects.count()
    total_profesores = CustomUser.objects.filter(user_type="profesor").count()
    total_estudiantes = CustomUser.objects.filter(user_type="estudiante").count()
    total_clases = Clase.objects.count()
    total_clases_finalizadas = Clase.objects.filter(finalizada=True).count()
    total_asistencias = AsistenciaClase.objects.filter(presente=True).count()
    porcentaje_asistencia = (
        100 * total_asistencias / AsistenciaClase.objects.count()
        if AsistenciaClase.objects.exists() else 0
    )

    # Estadísticas por sede
    sedes_stats = []
    for sede in sedes:
        carreras = sede.carreras.count()
        asignaturas = Asignatura.objects.filter(carrera__sede=sede).count()
        secciones = Seccion.objects.filter(asignatura__carrera__sede=sede).count()
        profesores = CustomUser.objects.filter(user_type='profesor', sede=sede).count()
        estudiantes = CustomUser.objects.filter(user_type='estudiante', sede=sede).count()
        clases = Clase.objects.filter(aula__sede=sede).count()
        clases_finalizadas = Clase.objects.filter(aula__sede=sede, finalizada=True).count()
        asistencia_total = AsistenciaClase.objects.filter(clase__aula__sede=sede, presente=True).count()
        asistencia_total_registros = AsistenciaClase.objects.filter(clase__aula__sede=sede).count()
        porc_asistencia = (
            100 * asistencia_total / asistencia_total_registros if asistencia_total_registros else 0
        )
        sedes_stats.append({
            "sede": sede,
            "carreras": carreras,
            "asignaturas": asignaturas,
            "secciones": secciones,
            "profesores": profesores,
            "estudiantes": estudiantes,
            "clases": clases,
            "clases_finalizadas": clases_finalizadas,
            "porc_asistencia": porc_asistencia,
        })

    asignaturas_qs = Asignatura.objects.all()
    if sede_actual:
        asignaturas_qs = asignaturas_qs.filter(carrera__sede=sede_actual)
    if carrera_actual:
        asignaturas_qs = asignaturas_qs.filter(carrera=carrera_actual)
    asignaturas_ranking = (
        asignaturas_qs.annotate(
            num_estudiantes=Count('secciones__relaciones_estudiantes_asignatura', distinct=True)
        )
        .order_by('-num_estudiantes')[:10]
    )

    context = {
        "total_sedes": total_sedes,
        "total_carreras": total_carreras,
        "total_asignaturas": total_asignaturas,
        "total_secciones": total_secciones,
        "total_profesores": total_profesores,
        "total_estudiantes": total_estudiantes,
        "total_clases": total_clases,
        "total_clases_finalizadas": total_clases_finalizadas,
        "total_asistencias": total_asistencias,
        "porcentaje_asistencia": porcentaje_asistencia,
        "sedes_stats": sedes_stats,
        "asignaturas_ranking": asignaturas_ranking,
        "fecha_generacion": timezone.now(),
        "sede_actual": sede_actual,
        "carrera_actual": carrera_actual,
        "admin_user": request.user,
    }

    template = get_template("core/dashboard_pdf.html")
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="dashboard_reporte.pdf"'

    pisa.CreatePDF(html, dest=response)
    return response




