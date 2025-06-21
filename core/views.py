# CORE/VIEWS.PY
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count

from datetime import timedelta
from django.contrib.auth.decorators import login_required, user_passes_test

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
@user_passes_test(admin_global_required)
def dashboard_admin_global(request):
    sede_id = request.GET.get("sede")
    carrera_id = request.GET.get("carrera")
    sede_actual = Sede.objects.filter(id=sede_id).first() if sede_id else None

    # --- CARRERAS SOLO DE LA SEDE SELECCIONADA ---
    if sede_actual:
        carreras = Carrera.objects.filter(sede=sede_actual)
    else:
        carreras = Carrera.objects.all()
    carrera_actual = carreras.filter(id=carrera_id).first() if carrera_id else None

    # --- FILTROS EN QUERIES ---
    # Aplicar filtros por Sede y luego por Carrera
    filtro = {}
    if sede_actual:
        filtro['carrera__sede'] = sede_actual
    if carrera_actual:
        filtro['carrera'] = carrera_actual

    filtro_sede = {}
    if sede_actual:
        filtro_sede['sede'] = sede_actual

    filtro_solo_sede = {}
    if sede_actual:
        filtro_solo_sede['aula__sede'] = sede_actual

    filtro_solo_carrera = {}
    if carrera_actual:
        filtro_solo_carrera['carrera'] = carrera_actual

    # --- MÉTRICAS GLOBALES ---
    total_sedes = Sede.objects.count()
    total_carreras = Carrera.objects.filter(**filtro_sede).count() if sede_actual else Carrera.objects.count()
    total_asignaturas = Asignatura.objects.filter(**filtro).count() if (sede_actual or carrera_actual) else Asignatura.objects.count()
    total_secciones = Seccion.objects.filter(asignatura__carrera__sede=sede_actual).count() if sede_actual else Seccion.objects.count()
    total_profesores = CustomUser.objects.filter(user_type="profesor", sede=sede_actual).count() if sede_actual else CustomUser.objects.filter(user_type="profesor").count()
    total_estudiantes = CustomUser.objects.filter(user_type="estudiante", sede=sede_actual).count() if sede_actual else CustomUser.objects.filter(user_type="estudiante").count()
    total_clases = Clase.objects.filter(**filtro_solo_sede).count() if sede_actual else Clase.objects.count()
    total_clases_finalizadas = Clase.objects.filter(finalizada=True, **filtro_solo_sede).count() if sede_actual else Clase.objects.filter(finalizada=True).count()
    total_asistencias = AsistenciaClase.objects.filter(clase__aula__sede=sede_actual, presente=True).count() if sede_actual else AsistenciaClase.objects.filter(presente=True).count()
    asistencia_registros = AsistenciaClase.objects.filter(clase__aula__sede=sede_actual).count() if sede_actual else AsistenciaClase.objects.count()
    porcentaje_asistencia = 100 * total_asistencias / asistencia_registros if asistencia_registros else 0

    # --- TABLA DE SEDES ---
    sedes_stats = []
    sedes_tabla = Sede.objects.all()
    for sede in sedes_tabla:
        carreras_q = Carrera.objects.filter(sede=sede)
        if carrera_actual:
            carreras_q = carreras_q.filter(id=carrera_actual.id)
        asignaturas_q = Asignatura.objects.filter(carrera__in=carreras_q)
        secciones_q = Seccion.objects.filter(asignatura__in=asignaturas_q)
        profesores_q = CustomUser.objects.filter(user_type="profesor", sede=sede)
        estudiantes_q = CustomUser.objects.filter(user_type="estudiante", sede=sede)
        clases_q = Clase.objects.filter(aula__sede=sede)
        clases_finalizadas_q = clases_q.filter(finalizada=True)
        asistencias_q = AsistenciaClase.objects.filter(clase__aula__sede=sede, presente=True)
        asistencias_totales = AsistenciaClase.objects.filter(clase__aula__sede=sede)
        if carrera_actual:
            asignaturas_q = asignaturas_q.filter(carrera=carrera_actual)
            secciones_q = secciones_q.filter(asignatura__carrera=carrera_actual)
            clases_q = clases_q.filter(seccion__asignatura__carrera=carrera_actual)
            clases_finalizadas_q = clases_finalizadas_q.filter(seccion__asignatura__carrera=carrera_actual)
            asistencias_q = asistencias_q.filter(clase__seccion__asignatura__carrera=carrera_actual)
            asistencias_totales = asistencias_totales.filter(clase__seccion__asignatura__carrera=carrera_actual)
            profesores_q = profesores_q.filter(carrera=carrera_actual)
            estudiantes_q = estudiantes_q.filter(carrera=carrera_actual)
        porc_asistencia = 100 * asistencias_q.count() / asistencias_totales.count() if asistencias_totales.count() else 0

        sedes_stats.append({
            "sede": sede,
            "carreras": carreras_q.count(),
            "asignaturas": asignaturas_q.count(),
            "secciones": secciones_q.count(),
            "profesores": profesores_q.count(),
            "estudiantes": estudiantes_q.count(),
            "clases": clases_q.count(),
            "clases_finalizadas": clases_finalizadas_q.count(),
            "porc_asistencia": porc_asistencia,
        })

     # --- TOP 10 ASIGNATURAS ---
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

    # --- Para select dinámico de carreras ---
    carreras_todas = Carrera.objects.filter(sede=sede_actual) if sede_actual else Carrera.objects.all()

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
        "sedes": Sede.objects.all(),
        "carreras": carreras_todas,
        "sede_actual": sede_actual,
        "carrera_actual": carrera_actual,
    }
    return render(request, "core/dashboard_admin_global.html", context)


















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



@login_required
@user_passes_test(is_admin_zona)
def dashboard_admin_zona(request):
    return render(request, 'core/dashboard_admin_zona.html', {
        'mensaje': '¡Bienvenido al Panel del Administrador de Zona!'
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