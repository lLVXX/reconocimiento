from django.db import models
from sedes.models import Sede, Seccion
from core.models import CustomUser

DIAS_SEMANA = [
    ('LU', 'Lunes'),
    ('MA', 'Martes'),
    ('MI', 'Miércoles'),
    ('JU', 'Jueves'),
    ('VI', 'Viernes'),
]

class BloqueHorario(models.Model):
    nombre = models.CharField(max_length=50)  # Ej: 'Bloque 1'
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
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)
    dia_semana = models.CharField(max_length=12, choices=DIAS_SEMANA)
    bloque_horario = models.ForeignKey(BloqueHorario, on_delete=models.CASCADE)
    profesor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'profesor'})
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.get_dia_semana_display()} - {self.seccion.nombre} - {self.profesor}"