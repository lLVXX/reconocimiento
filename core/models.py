from django.contrib.auth.models import AbstractUser
from django.db import models
from sedes.models import Sede
from sedes.models import Asignatura


from django.contrib.auth.models import AbstractUser
from django.db import models
from sedes.models import Sede, Carrera, Asignatura

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin_global', 'Administrador Global'),
        ('admin_zona', 'Administrador Zona'),
        ('profesor', 'Profesor'),
        ('estudiante', 'Estudiante'),
    )

    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    carrera = models.ForeignKey(Carrera, null=True, blank=True, on_delete=models.SET_NULL)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios_sede')
    workzone = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios_workzone')
    asignaturas = models.ManyToManyField(Asignatura, blank=True, related_name='profesores')  # ← agregado



    # Campos exclusivos para estudiantes
    imagen = models.ImageField(upload_to='estudiantes/', null=True, blank=True)
    motivo_cambio = models.TextField(null=True, blank=True)

    

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

##################################################################


