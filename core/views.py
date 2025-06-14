# Standard Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count

# Formularios propios
from .forms import CustomLoginForm, AdminZonaForm
from personas.forms import EstudianteForm

# Modelos propios
from .models import CustomUser
from sedes.models import Seccion

# Decoradores y utilidades personalizadas
from core.decorators import admin_zona_required
from core.utils import admin_global_required

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


###############################################################

