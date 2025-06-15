#clases/forms.py

from django import forms
from .models import Aula, BloqueHorario, Clase
from sedes.models import  Seccion, Carrera, Asignatura
from personas.models import CustomUser







class AulaForm(forms.ModelForm):
    class Meta:
        model = Aula
        fields = ['numero_sala', 'ip_camara']
        widgets = {
            'numero_sala': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 101'}),
            'ip_camara': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'rtsp://...' }),
        }

    
class BloqueHorarioForm(forms.ModelForm):
    class Meta:
        model = BloqueHorario
        fields = ['nombre', 'hora_inicio', 'hora_fin']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }


DIAS_SEMANA = [
    ('LU', 'Lunes'),
    ('MA', 'Martes'),
    ('MI', 'Miércoles'),
    ('JU', 'Jueves'),
    ('VI', 'Viernes'),
]

# --- Campo personalizado para mostrar todo el detalle de la seccion ---
class SeccionModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.nombre} - {obj.asignatura.nombre} - {obj.asignatura.carrera.nombre}"

class ClaseForm(forms.ModelForm):
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.none(),
        label="Carrera",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    asignatura = forms.ModelChoiceField(
        queryset=Asignatura.objects.none(),
        label="Asignatura",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    seccion = SeccionModelChoiceField(
        queryset=Seccion.objects.none(),
        label="Sección",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    dia_semana = forms.ChoiceField(
        choices=DIAS_SEMANA,   # <---- Usa los choices del modelo
        label="Día de la semana",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Clase
        fields = ['carrera', 'asignatura', 'seccion', 'dia_semana', 'bloque_horario', 'aula', 'profesor']
        widgets = {
            'bloque_horario': forms.Select(attrs={'class': 'form-control'}),
            'aula': forms.Select(attrs={'class': 'form-control'}),
            'profesor': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            sede = getattr(user, "sede", None)
            self.fields['carrera'].queryset = Carrera.objects.filter(sede=sede)
            self.fields['aula'].queryset = Aula.objects.filter(sede=sede)
            self.fields['profesor'].queryset = CustomUser.objects.filter(user_type='profesor', sede=sede)
        else:
            self.fields['carrera'].queryset = Carrera.objects.all()
            self.fields['aula'].queryset = Aula.objects.all()
            self.fields['profesor'].queryset = CustomUser.objects.filter(user_type='profesor')

        # --- Dependencias dinámicas ---
        if self.data.get('carrera'):
            try:
                carrera_id = int(self.data.get('carrera'))
                self.fields['asignatura'].queryset = Asignatura.objects.filter(carrera_id=carrera_id)
            except (ValueError, TypeError):
                self.fields['asignatura'].queryset = Asignatura.objects.none()
        elif self.instance.pk:
            self.fields['asignatura'].queryset = Asignatura.objects.filter(carrera=self.instance.seccion.asignatura.carrera)
        else:
            self.fields['asignatura'].queryset = Asignatura.objects.none()

        if self.data.get('asignatura'):
            try:
                asignatura_id = int(self.data.get('asignatura'))
                self.fields['seccion'].queryset = Seccion.objects.filter(asignatura_id=asignatura_id)
            except (ValueError, TypeError):
                self.fields['seccion'].queryset = Seccion.objects.none()
        elif self.instance.pk:
            self.fields['seccion'].queryset = Seccion.objects.filter(asignatura=self.instance.seccion.asignatura)
        else:
            self.fields['seccion'].queryset = Seccion.objects.none()