# PERSONAS/FORMS.PY

from django import forms
from core.models import CustomUser
from sedes.models import Carrera, Asignatura, Seccion
from personas.models import EstudianteAsignaturaSeccion
from django.db.models import Count

from personas.models import EstudianteAsignaturaSeccion, EstudianteFoto
import numpy as np

from django.core.exceptions import ValidationError



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
    imagen = forms.ImageField(
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label="Foto del estudiante"
    )
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

    def clean_imagen(self):
        img = self.cleaned_data.get('imagen')
        if not img:
            raise ValidationError("Debe subir una foto para generar el embedding.")
        return img

    def save(self, commit=True):
        estudiante = super().save(commit=False)
        estudiante.user_type = 'estudiante'
        estudiante.sede = self.user.sede
        estudiante.carrera = self.cleaned_data['carrera']

        # Genera username & email
        nombre = estudiante.first_name.strip().lower()
        apellido = estudiante.last_name.strip().lower()
        dominio = estudiante.sede.nombre.lower().replace(' ', '')
        correo = f"{nombre[:2]}.{apellido}@{dominio}.com"
        estudiante.email = correo
        estudiante.username = correo

        # Password por defecto
        if not self.instance.pk:
            estudiante.set_password('12345678')

        if commit:
            estudiante.save()
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
