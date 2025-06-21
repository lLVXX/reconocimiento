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
def dashboard_admin_global(request):
    return render(request, 'core/dashboard_admin_global.html')


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
