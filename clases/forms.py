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
    ('SA', 'Sábado'),
]


class SeccionModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Muestra más info al usuario
        return f"{obj.nombre} - {obj.asignatura.nombre} - {obj.asignatura.carrera.nombre}"




class ClaseForm(forms.ModelForm):
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.none(),
        label="Carrera",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_carrera'})
    )
    asignatura = forms.ModelChoiceField(
        queryset=Asignatura.objects.none(),
        label="Asignatura",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_asignatura'})
    )
    seccion = forms.ModelChoiceField(
        queryset=Seccion.objects.none(),
        label="Sección",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_seccion'})
    )

    class Meta:
        model = Clase
        fields = [
            'carrera', 'asignatura', 'seccion',
            'dia_semana', 'bloque_horario', 'aula', 'profesor'
        ]
        widgets = {
            'bloque_horario': forms.Select(attrs={'class': 'form-select'}),
            'aula': forms.Select(attrs={'class': 'form-select'}),
            'profesor': forms.HiddenInput(),
            'dia_semana': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, "sede"):
            self.fields['carrera'].queryset = Carrera.objects.filter(sede=user.sede)
            self.fields['aula'].queryset = Aula.objects.filter(sede=user.sede)
        else:
            self.fields['carrera'].queryset = Carrera.objects.all()
            self.fields['aula'].queryset = Aula.objects.all()
        carrera_id = (
            self.data.get('carrera')
            or (self.initial.get('carrera').id if self.initial.get('carrera') else None)
            or (self.instance.seccion.asignatura.carrera.id if getattr(self.instance, 'seccion', None) else None)
        )
        if carrera_id:
            self.fields['asignatura'].queryset = Asignatura.objects.filter(carrera_id=carrera_id)
        else:
            self.fields['asignatura'].queryset = Asignatura.objects.none()
        asignatura_id = (
            self.data.get('asignatura')
            or (self.initial.get('asignatura').id if self.initial.get('asignatura') else None)
            or (self.instance.seccion.asignatura.id if getattr(self.instance, 'seccion', None) else None)
        )
        if asignatura_id:
            self.fields['seccion'].queryset = Seccion.objects.filter(asignatura_id=asignatura_id)
        else:
            self.fields['seccion'].queryset = Seccion.objects.none()
#################### ASIS MANUAL #############3


class AsistenciaManualForm(forms.Form):
    def __init__(self, estudiantes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for estudiante in estudiantes:
            self.fields[f"presente_{estudiante.id}"] = forms.BooleanField(
                label=estudiante.get_full_name(),
                required=False,
                initial=False
            )