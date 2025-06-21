from django.db import models
from sedes.models import Sede, Seccion
from core.models import CustomUser, SemanaAcademica  # <-- SemanaAcademica debe estar en core.models
from django.utils import timezone

DIAS_SEMANA = [
    ('LU', 'Lunes'),
    ('MA', 'Martes'),
    ('MI', 'Miércoles'),
    ('JU', 'Jueves'),
    ('VI', 'Viernes'),
]

class BloqueHorario(models.Model):
    nombre = models.CharField(max_length=50)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    def __str__(self):
        return f"{self.nombre} ({self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')})"

class Aula(models.Model):
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)
    numero_sala = models.CharField(max_length=10)
    ip_camara = models.CharField(max_length=100, blank=True, help_text="Puede estar vacía si se usa webcam local")

    def __str__(self):
        return f"Sala {self.numero_sala} - {self.sede.nombre}"

class Clase(models.Model):
    aula = models.ForeignKey('Aula', on_delete=models.CASCADE)
    dia_semana = models.CharField(max_length=12, choices=DIAS_SEMANA)
    bloque_horario = models.ForeignKey('BloqueHorario', on_delete=models.CASCADE)
    profesor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'profesor'})
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE)

    fecha = models.DateField(null=True, blank=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    semana_academica = models.ForeignKey(
        SemanaAcademica,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clases',
        help_text="Semana académica a la que corresponde la clase"
    )

    finalizada = models.BooleanField(default=False)
    consolidada = models.BooleanField(default=False)

    total_estudiantes = models.PositiveIntegerField(default=0)
    presentes = models.PositiveIntegerField(default=0)
    ausentes = models.PositiveIntegerField(default=0)
    porcentaje_asistencia = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.get_dia_semana_display()} - {self.seccion.nombre} - {self.profesor}"

###########################################
###     LOG DE CLASES / ASISTENCIA      ###
###########################################

class AsistenciaClase(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='asistencias')
    estudiante = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'estudiante'})
    presente = models.BooleanField(default=False)
    manual = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('clase', 'estudiante')

    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.clase} - {'Presente' if self.presente else 'Ausente'}"

class HistorialAsistenciaClase(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='historial_asistencias')
    estudiante = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    presente = models.BooleanField(default=False)
    timestamp = models.DateTimeField()
    origen = models.CharField(max_length=20, choices=[
        ('facial', 'Reconocimiento Facial'),
        ('manual', 'Manual'),
    ])
    consolidado = models.BooleanField(default=False)

    def __str__(self):
        return f"[Historial] {self.estudiante.get_full_name()} - {self.clase}"

class AuditoriaAsistencia(models.Model):
    historial = models.ForeignKey(HistorialAsistenciaClase, on_delete=models.CASCADE)
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    accion = models.CharField(max_length=30)
    timestamp = models.DateTimeField(default=timezone.now)
    detalles = models.TextField(blank=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.accion} - {self.timestamp}"
