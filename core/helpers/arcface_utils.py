import insightface
import numpy as np
import cv2

_model = None

def cargar_modelo():
    global _model
    if _model is None:
        _model = insightface.app.FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
        _model.prepare(ctx_id=0, det_size=(640, 640))
    return _model

def generar_embedding_from_file(file):
    model = cargar_modelo()
    arr = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        print("No se pudo decodificar la imagen.")
        return None
    faces = model.get(img)
    if not faces:
        print("No se detectó rostro.")
        return None
    return faces[0]['embedding']
