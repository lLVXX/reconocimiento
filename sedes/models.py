from django.db import models


class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Carrera(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    sede = models.ForeignKey("sedes.Sede", on_delete=models.CASCADE, related_name='carreras')

    def __str__(self):
        return f"{self.nombre} ({self.sede.nombre})"
        


class Asignatura(models.Model):
    nombre = models.CharField(max_length=100)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre
    

class Seccion(models.Model):
    asignatura = models.ForeignKey('Asignatura', on_delete=models.CASCADE, related_name="secciones")
    nombre = models.CharField(max_length=100)