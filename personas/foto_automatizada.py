# personas/foto_automatizada.py

from personas.models import EstudianteFoto
from core.helpers.arcface_utils import generar_embedding_from_file

def guardar_foto_automatica(estudiante, imagen_file):
    """
    Agrega una nueva foto automática después de clase.
    - Mantiene como máximo 4 fotos automáticas.
    - Si ya hay 4, elimina la más antigua.
    - Solo debe llamarse cuando el sistema decida guardar una foto tras asistencia.
    """
    imagen_file.seek(0)
    embedding = generar_embedding_from_file(imagen_file)
    if embedding is None:
        return False  # Si no hay rostro, no se guarda

    # Fotos automáticas existentes
    fotos_auto = EstudianteFoto.objects.filter(estudiante=estudiante, es_base=False).order_by('fecha_creacion')
    if fotos_auto.count() >= 4:
        fotos_auto.first().delete()  # Elimina la más antigua

    nueva_foto = EstudianteFoto.objects.create(
        estudiante=estudiante,
        imagen=imagen_file,
        embedding=embedding.tobytes(),
        es_base=False
    )
    return True
