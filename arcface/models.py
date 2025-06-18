# arcface/models.py
from django.db import models
from personas.models import CustomUser

class FaceEmbedding(models.Model):
    estudiante = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='embeddings')
    embedding = models.BinaryField()  # Guarda el vector como bytes (o usa JSONField si prefieres serializar)
    creado_en = models.DateTimeField(auto_now_add=True)
    orden = models.PositiveSmallIntegerField(default=1)  # 1: primer embedding, 2..5: los demás
    activo = models.BooleanField(default=True)  # Por si quieres desactivar alguno en el futuro

    class Meta:
        unique_together = ('estudiante', 'orden')