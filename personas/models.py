# PERSONAS/MODELS.PY

from django.db import models
from core.models import CustomUser
from sedes.models import Asignatura, Seccion, Carrera



#############################################################


def ruta_imagen_estudiante(instance, filename):
    return f"estudiantes/{instance.rut}_{filename}"



class EstudianteAsignaturaSeccion(models.Model):
    estudiante = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name="relaciones_asignatura_seccion"
    )
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    seccion = models.ForeignKey(
        Seccion, 
        on_delete=models.CASCADE, 
        related_name="relaciones_estudiantes_asignatura"
    )

    class Meta:
        unique_together = ('estudiante', 'asignatura')

    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.asignatura.nombre} ({self.seccion.nombre})"
    


############################ ARCFACE ########################################3

class EstudianteFoto(models.Model):
    estudiante = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='fotos')
    imagen = models.ImageField(upload_to='estudiantes/fotos_extra/')
    embedding = models.BinaryField(blank=True, null=True)
    es_base = models.BooleanField(default=False)  # True solo para la de registro inicial
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        tipo = "BASE" if self.es_base else "AUTO"
        return f"{self.estudiante} - {tipo} - {self.fecha_creacion}"