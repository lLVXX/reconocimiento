# reconocimiento/arcface/embedding_utils.py

import requests

def calcular_embedding_microservicio(path_imagen):
    url = "http://localhost:8000/embedding/"
    with open(path_imagen, "rb") as f:
        files = {'file': f}
        r = requests.post(url, files=files)
    data = r.json()
    if "embedding" not in data:
        raise Exception("No se pudo calcular embedding: " + str(data.get("error")))
    return data["embedding"]
