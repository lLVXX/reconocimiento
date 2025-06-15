#clases/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.decorators import admin_zona_required
from django.contrib import messages
from .models import BloqueHorario
from .forms import BloqueHorarioForm
from django.db.models import Count
from .models import Aula
from .forms import AulaForm
from .forms import ClaseForm
from .models import Clase
from sedes.models import Seccion, Asignatura
from django.http import JsonResponse, HttpResponseForbidden

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

    bloques = BloqueHorario.objects.all().order_by('hora_inicio')  # <-- corregido aquí
    return render(request, 'clases/gestionar_bloques_horarios.html', {
        'form': form,
        'bloques': bloques,
        'editar_id': editar_id,
    })





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




####################

def obtener_secciones_por_sede(sede):
    from sedes.models import Seccion
    return Seccion.objects.filter(asignatura__carrera__sede=sede)

@login_required
def ajax_secciones_por_carrera(request):
    carrera_id = request.GET.get('carrera_id')
    secciones = []
    if carrera_id:
        for seccion in Seccion.objects.filter(asignatura__carrera_id=carrera_id):
            nombre_completo = f"{seccion.nombre} - {seccion.asignatura.nombre} - {seccion.asignatura.carrera.nombre}"
            secciones.append({
                'id': seccion.id,
                'text': nombre_completo
            })
    return JsonResponse({'secciones': secciones})




#######################################################


@login_required
def gestionar_clases(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")
    user = request.user
    sede = getattr(user, "sede", None)
    
    if eliminar_id:
        clase = get_object_or_404(Clase, id=eliminar_id)
        clase.delete()
        messages.success(request, "Clase eliminada correctamente.")
        return redirect("gestionar_clases")
    
    if editar_id:
        clase = get_object_or_404(Clase, id=editar_id)
        form = ClaseForm(request.POST or None, instance=clase, user=request.user)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, "Clase actualizada correctamente.")
            return redirect("gestionar_clases")
    else:
        form = ClaseForm(request.POST or None, user=request.user)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, "Clase creada correctamente.")
            return redirect("gestionar_clases")
    
    clases = Clase.objects.filter(aula__sede=sede).select_related("aula", "bloque_horario", "profesor", "seccion")
    return render(request, "clases/gestionar_clases.html", {
        "form": form,
        "clases": clases,
    })

# --- Endpoints AJAX ---
@login_required
def get_asignaturas_ajax(request):
    carrera_id = request.GET.get('carrera_id')
    asignaturas = Asignatura.objects.filter(carrera_id=carrera_id).values('id', 'nombre')
    return JsonResponse(list(asignaturas), safe=False)

@login_required
def get_secciones_ajax(request):
    asignatura_id = request.GET.get('asignatura_id')
    secciones = Seccion.objects.filter(asignatura_id=asignatura_id).values('id', 'nombre')
    return JsonResponse(list(secciones), safe=False)


#######################################################


@login_required
@admin_zona_required
def resumen_estudiantes_por_seccion(request):
    sede_actual = request.user.sede
    secciones = Seccion.objects.filter(
        asignatura__carrera__sede=sede_actual
    ).annotate(num_estudiantes=Count('estudiantes')).order_by('asignatura__carrera__nombre', 'nombre')

    context = {
        'secciones': secciones,
        'sede': sede_actual,
    }
    return render(request, 'clases/resumen_secciones.html', context)



############# PROFESOR ###############


@login_required
def dashboard_profesor(request):
    clases = Clase.objects.filter(profesor=request.user).select_related(
        'aula', 'bloque_horario', 'seccion', 'seccion__asignatura', 'seccion__asignatura__carrera', 'aula__sede'
    )
    return render(request, 'clases/dashboard_profesor.html', {
        'clases': clases
    })