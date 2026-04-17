import os
import numpy as np
from deepface import DeepFace


def _iou(boxA, boxB):
    """Compute Intersection-over-Union of two bounding boxes."""
    xA = max(boxA["x"], boxB["x"])
    yA = max(boxA["y"], boxB["y"])
    xB = min(boxA["x"] + boxA["w"], boxB["x"] + boxB["w"])
    yB = min(boxA["y"] + boxA["h"], boxB["y"] + boxB["h"])

    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH

    if interArea == 0:
        return 0.0

    areaA = boxA["w"] * boxA["h"]
    areaB = boxB["w"] * boxB["h"]
    return interArea / float(areaA + areaB - interArea)


def _nms(faces, iou_threshold=0.25):
    """
    Non-Maximum Suppression: removes duplicate/overlapping face detections.
    Keeps the detection with the larger bounding box area when two boxes
    overlap significantly.
    """
    if not faces:
        return faces

    # Sort by area descending (largest = most confident detection first)
    faces = sorted(faces, key=lambda f: f["box"]["w"] * f["box"]["h"], reverse=True)

    kept = []
    for candidate in faces:
        suppressed = False
        for kept_face in kept:
            if _iou(candidate["box"], kept_face["box"]) > iou_threshold:
                suppressed = True
                break
        if not suppressed:
            kept.append(candidate)

    return kept


def get_faces_data(image_path):
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name="ArcFace",
            detector_backend="retinaface",
            enforce_detection=False
        )

        print(f"[deepface] Raw detections from retinaface: {len(result)}")

        faces = []

        for r in result:
            emb = r["embedding"]
            region = r["facial_area"]  # bounding box dict: {x, y, w, h}

            # Skip detections with a very low face confidence score
            face_conf = r.get("face_confidence", 1.0)
            print(f"[deepface] Detection box={region}, confidence={face_conf:.3f}")
            if face_conf < 0.5:
                print(f"[deepface] -> Skipping (low confidence)")
                continue

            box = {
                "x": region.get("x", 0),
                "y": region.get("y", 0),
                "w": region.get("w", 0),
                "h": region.get("h", 0),
            }

            faces.append({"embedding": emb, "box": box})

        print(f"[deepface] After confidence filter: {len(faces)} face(s)")

        # Drop tiny background faces — configurable via MIN_FACE_PX env var
        MIN_FACE_PX = int(os.getenv("MIN_FACE_PX", "80"))
        faces = [f for f in faces if f["box"]["w"] >= MIN_FACE_PX and f["box"]["h"] >= MIN_FACE_PX]
        print(f"[deepface] After size filter (min {MIN_FACE_PX}px): {len(faces)} face(s)")

        # Deduplicate overlapping detections (Non-Maximum Suppression)
        faces = _nms(faces)
        print(f"[deepface] After NMS: {len(faces)} face(s)")

        return faces

    except Exception as e:
        print("Error in get_faces_data:", e)
        return []