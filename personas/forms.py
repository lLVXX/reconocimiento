# PERSONAS/FORMS.PY

from django import forms
from core.models import CustomUser
from sedes.models import Carrera, Asignatura, Seccion
from personas.models import EstudianteAsignaturaSeccion
from django.db.models import Count



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
        print("==== EJECUTANDO SAVE DE ESTUDIANTE FORM ====")
        estudiante = super().save(commit=False)
        estudiante.user_type = 'estudiante'
        estudiante.sede = self.user.sede
        estudiante.carrera = self.cleaned_data['carrera']

        nombre = estudiante.first_name.strip().lower()
        apellido = estudiante.last_name.strip().lower()
        correo = f"{nombre[:2]}.{apellido}@{estudiante.sede.nombre.lower().replace(' ', '')}.com"
        estudiante.email = correo
        estudiante.username = correo
        estudiante.set_password('12345678')

        if commit:
            estudiante.save()
            # Obtén todas las asignaturas de la carrera seleccionada
            asignaturas = Asignatura.objects.filter(carrera=estudiante.carrera)
            print(">>> Asignaturas encontradas:", list(asignaturas))
            for asignatura in asignaturas:
                print(">>> Procesando asignatura:", asignatura)
                secciones = Seccion.objects.filter(asignatura=asignatura).annotate(
                    num_estudiantes=Count('estudiantes_asignatura')
                )
                seccion_asignada = None
                for seccion in secciones:
                    if seccion.num_estudiantes < 30:
                        seccion_asignada = seccion
                        break
                if not seccion_asignada:
                    nombre_seccion = generar_nombre_seccion(asignatura)
                    print(f">>> Creando nueva sección: {nombre_seccion}")
                    seccion_asignada = Seccion.objects.create(nombre=nombre_seccion, asignatura=asignatura)
                print(f">>> Asignando estudiante a sección: {seccion_asignada}")
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
