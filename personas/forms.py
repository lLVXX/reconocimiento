from django import forms
from core.models import CustomUser
from sedes.models import Carrera
from .models import Asignatura, Seccion

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

class EstudianteForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, label='Nombre')
    last_name = forms.CharField(max_length=100, label='Apellido')
    rut = forms.CharField(max_length=12, label='RUT')
    carrera = forms.ModelChoiceField(queryset=Carrera.objects.none(), label='Carrera')
    imagen = forms.ImageField(required=False, label='Foto')

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'rut', 'carrera', 'imagen']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['carrera'].queryset = Carrera.objects.filter(sede=user.sede)

    def clean_rut(self):
        rut = self.cleaned_data['rut'].replace(".", "").replace("-", "").upper()
        return rut

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
