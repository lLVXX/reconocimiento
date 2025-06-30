# personas/tasks.py

import base64
import json
import requests
from celery import shared_task
from django.conf import settings
from .models import EstudianteFoto

@shared_task
def procesar_captura(foto_id: int, img_b64: str):
    """
    Toma el ID de EstudianteFoto y su base64, llama al microservicio
    para obtener embedding, y lo guarda.
    """
    try:
        foto = EstudianteFoto.objects.get(id=foto_id)
    except EstudianteFoto.DoesNotExist:
        return f"Foto {foto_id} no encontrada"

    # Preparamos el archivo para el POST multipart
    header, img_str = img_b64.split(';base64,')
    ext = header.split('/')[-1]
    data = base64.b64decode(img_str)

    try:
        resp = requests.post(
            f"{settings.ARC_FACE_URL}/generar_embedding/",
            files={'file': (foto.imagen.name, data, f"image/{ext}")}
        )
        resp.raise_for_status()
        data_emb = resp.json()
        if data_emb.get('ok') and 'embedding' in data_emb:
            foto.embedding = data_emb['embedding']
            foto.save(update_fields=['embedding'])
            return f"Embedding guardado para foto {foto_id}"
        else:
            return f"No se obtuvo embedding válido para foto {foto_id}"
    except Exception as e:
        return f"Error al procesar foto {foto_id}: {e}"
