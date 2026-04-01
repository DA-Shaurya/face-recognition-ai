import numpy as np
from deepface import DeepFace

def get_faces_data(image_path):
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name="VGG-Face",
            detector_backend="retinaface",
            enforce_detection=False
        )

        faces = []

        for r in result:
            emb = r["embedding"]
            region = r["facial_area"]  # 👈 bounding box

            faces.append({
                "embedding": emb,
                "box": region
            })

        return faces

    except Exception as e:
        print("Error:", e)
        return []