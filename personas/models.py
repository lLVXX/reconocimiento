from django.db import models
from sedes.models import Carrera, Sede
from core.models import CustomUser

class Asignatura(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='asignaturas')

    def __str__(self):
        return f"{self.nombre} ({self.carrera.nombre})"



class Seccion(models.Model):
    nombre = models.CharField(max_length=20)
    asignatura = models.ForeignKey("personas.Asignatura", on_delete=models.CASCADE, related_name="secciones")

    def __str__(self):
        return f"{self.nombre} - {self.asignatura.nombre}"





#############################################################


def ruta_imagen_estudiante(instance, filename):
    return f"estudiantes/{instance.rut}_{filename}"


class EstudianteAsignaturaSeccion(models.Model):
    estudiante = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'estudiante'})
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('estudiante', 'asignatura')

    def __str__(self):
        return f"{self.estudiante} - {self.asignatura} -> {self.seccion}"
