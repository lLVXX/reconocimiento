# PERSONAS/FORMS.PY

from django import forms
from core.models import CustomUser
from sedes.models import Carrera, Asignatura, Seccion
from personas.models import EstudianteAsignaturaSeccion
from django.db.models import Count

from personas.models import EstudianteAsignaturaSeccion, EstudianteFoto
from core.helpers.arcface_microservice import obtener_embedding_desde_microservicio
import numpy as np





# ------------------------------------------------------------
# Formulario para PROFESOR (usa CustomUser + asignaturas)
# ------------------------------------------------------------
class ProfesorForm(forms.ModelForm):
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre'
        })
    )
    apellido = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido'
        })
    )
    rut = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12.345.678-9',
            'id': 'rut-input'
        })
    )
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    asignaturas = forms.ModelMultipleChoiceField(
        queryset=Asignatura.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = CustomUser
        fields = ['nombre', 'apellido', 'rut', 'carrera', 'asignaturas']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['carrera'].queryset = Carrera.objects.filter(sede=user.sede)


# ------------------------------------------------------------
# Formulario para ESTUDIANTE (usa CustomUser + imagen)
# ------------------------------------------------------------

def generar_nombre_seccion(asignatura):
    sufijos = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    existentes = set(Seccion.objects.filter(asignatura=asignatura).values_list('nombre', flat=True))
    for i in range(1, 1000):
        for letra in sufijos:
            nombre = f"{i:03}{letra}"
            if nombre not in existentes:
                return nombre


class EstudianteForm(forms.ModelForm):
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label="Carrera"
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'rut', 'carrera', 'imagen', 'motivo_cambio']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['carrera'].queryset = Carrera.objects.filter(sede=self.user.sede)

    def save(self, commit=True):
        estudiante = super().save(commit=False)
        estudiante.user_type = 'estudiante'
        estudiante.sede = self.user.sede
        estudiante.carrera = self.cleaned_data['carrera']

        nombre = estudiante.first_name.strip().lower()
        apellido = estudiante.last_name.strip().lower()
        correo = f"{nombre[:2]}.{apellido}@{estudiante.sede.nombre.lower().replace(' ', '')}.com"
        estudiante.email = correo
        estudiante.username = correo
        if not self.instance.pk:
            estudiante.set_password('12345678')

        if commit:
            estudiante.save()
            # FOTO BASE Y EMBEDDING SOLO SI NO EXISTE YA
            imagen_file = self.cleaned_data.get('imagen')
            if imagen_file and not EstudianteFoto.objects.filter(estudiante=estudiante, es_base=True).exists():
                imagen_file.seek(0)
                embedding = obtener_embedding_desde_microservicio(imagen_file)
                if embedding is None:
                    raise forms.ValidationError("No se detectó rostro en la imagen o el microservicio no respondió correctamente.")
                foto_base = EstudianteFoto(
                    estudiante=estudiante,
                    imagen=imagen_file,
                    embedding=np.array(embedding, dtype='float32').tobytes(),
                    es_base=True
                )
                foto_base.save()
                imagen_file.seek(0)
            # ASIGNACIÓN DE SECCIONES
            asignaturas = Asignatura.objects.filter(carrera=estudiante.carrera)
            for asignatura in asignaturas:
                secciones = Seccion.objects.filter(asignatura=asignatura).annotate(
                    num_estudiantes=Count('relaciones_estudiantes_asignatura')
                )
                seccion_asignada = None
                for seccion in secciones:
                    if seccion.num_estudiantes < 30:
                        seccion_asignada = seccion
                        break
                if not seccion_asignada:
                    nombre_seccion = f"{asignatura.nombre[:6]}-{asignatura.id}A"
                    seccion_asignada = Seccion.objects.create(nombre=nombre_seccion, asignatura=asignatura)
                EstudianteAsignaturaSeccion.objects.get_or_create(
                    estudiante=estudiante,
                    asignatura=asignatura,
                    defaults={'seccion': seccion_asignada}
                )
            self.save_m2m()
        return estudiante

# ------------------------------------------------------------
# Formularios auxiliares para CRUD
# ------------------------------------------------------------
class SeccionForm(forms.ModelForm):
    class Meta:
        model = Seccion
        fields = ['nombre', 'asignatura']


class AsignaturaForm(forms.ModelForm):
    class Meta:
        model = Asignatura
        fields = ['nombre', 'carrera']
