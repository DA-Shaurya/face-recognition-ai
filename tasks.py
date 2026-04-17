"""
tasks.py — Celery background tasks.
Imports celery from celery_app (not app) to avoid circular imports.
DB access works because app.py wraps all tasks in ContextTask.
"""
import os
import json
import time
import glob
import redis
import cv2
import numpy as np
from celery_app import celery
from utils.database import db, Person, ImageRecord, FaceEmbedding
from utils.deepface_utils import get_faces_data
from utils.recognition import find_person
from utils.clustering import cluster_faces

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

UPLOAD_FOLDER = "static/uploads"


def _draw_boxes(img_path, detections):
    img = cv2.imread(img_path)
    if img is None:
        return img_path
    for det in detections:
        name = det["name"]
        conf = det["confidence"]
        box  = det["box"]
        x, y, w, h = box["x"], box["y"], box["w"], box["h"]
        color = (0, 220, 110) if not name.startswith("Unknown") else (60, 60, 220)
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        label = f"{name}  {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(img, (x, y - th - 8), (x + tw + 6, y), color, -1)
        cv2.putText(img, label, (x + 3, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    filename = os.path.basename(img_path)
    out_path = os.path.join(os.path.dirname(img_path), "boxed_" + filename)
    cv2.imwrite(out_path, img)
    return "boxed_" + filename


@celery.task(name="tasks.process_uploaded_images_task")
def process_uploaded_images_task(session_id, saved_files_data, conf_threshold, margin_threshold):
    total = len(saved_files_data)
    file_names     = []
    all_detections = []
    boxed_images   = []

    for i, file_data in enumerate(saved_files_data):
        original_name = file_data["original_name"]
        raw_path      = file_data["filepath"]
        file_hash     = file_data.get("file_hash")

        redis_client.publish(f"progress_{session_id}", json.dumps({
            "type": "progress", "file": original_name, "step": i + 1, "total": total
        }))

        # ── Deduplication: skip re-processing known hashes ───────────────────
        existing_img = None
        if file_hash:
            existing_img = ImageRecord.query.filter_by(file_hash=file_hash).first()

        if existing_img:
            print(f"[tasks] Duplicate: {original_name} — reusing existing record")
            existing_faces = FaceEmbedding.query.filter_by(image_id=existing_img.id).all()
            detections = []
            for face in existing_faces:
                person = db.session.get(Person, face.person_id) if face.person_id else None
                detections.append({
                    "name":       person.name if person else "Unknown",
                    "confidence": face.confidence,
                    "box":        face.bounding_box,
                    "embedding":  face.embedding.tolist() if hasattr(face.embedding, "tolist") else list(face.embedding),
                })
            file_names.append(existing_img.filename)
            all_detections.append(detections)
            boxed_images.append({"original": existing_img.filename, "boxed": "boxed_" + existing_img.filename})
            redis_client.publish(f"progress_{session_id}", json.dumps({
                "type": "file_done", "file": original_name, "faces": len(detections)
            }))
            continue

        # ── New image — run DeepFace ──────────────────────────────────────────
        faces      = get_faces_data(raw_path)
        detections = []

        new_img = ImageRecord(
            filename=file_data["filename"],
            original_name=original_name,
            filepath=raw_path,
            file_hash=file_hash,
        )
        db.session.add(new_img)
        db.session.commit()

        for face in faces:
            name, distance = find_person(
                face["embedding"],
                threshold=conf_threshold,
                margin=margin_threshold,
            )
            confidence = max(0.0, 1.0 - (distance / 2.0))
            detections.append({
                "name":       name,
                "confidence": confidence,
                "box":        face["box"],
                "embedding":  face["embedding"],
            })
            person = Person.query.filter_by(name=name).first() if name != "Unknown" else None
            db.session.add(FaceEmbedding(
                person_id=person.id if person else None,
                image_id=new_img.id,
                embedding=face["embedding"],
                bounding_box=face["box"],
                confidence=confidence,
            ))

        db.session.commit()
        boxed_filename = _draw_boxes(raw_path, detections)
        file_names.append(file_data["filename"])
        all_detections.append(detections)
        boxed_images.append({"original": file_data["filename"], "boxed": boxed_filename})
        redis_client.publish(f"progress_{session_id}", json.dumps({
            "type": "file_done", "file": original_name, "faces": len(detections)
        }))

    # ── Build albums — cluster unknown faces with DBSCAN ─────────────────────
    albums         = {}
    unknown_entries = []  # {embedding, image, confidence}

    for filename, detections in zip(file_names, all_detections):
        for det in detections:
            if det["name"] != "Unknown":
                albums.setdefault(det["name"], []).append({
                    "image": filename, "confidence": det["confidence"]
                })
            else:
                unknown_entries.append({
                    "embedding":  det["embedding"],
                    "image":      filename,
                    "confidence": det["confidence"],
                })

    # DBSCAN cluster unknown faces → "Unknown #1", "Unknown #2", …
    if unknown_entries:
        embs   = np.array([e["embedding"] for e in unknown_entries], dtype=np.float32)
        labels = cluster_faces(embs)  # returns array of int cluster ids (-1 = noise)
        for entry, label in zip(unknown_entries, labels):
            cluster_key = f"Unknown #{label + 1}" if label >= 0 else "Unknown"
            albums.setdefault(cluster_key, []).append({
                "image": entry["image"], "confidence": entry["confidence"]
            })

    redis_client.publish(f"progress_{session_id}", json.dumps({
        "type": "done", "albums": albums, "boxed_images": boxed_images
    }))
    redis_client.set(f"result_{session_id}_albums", json.dumps(albums), ex=3600)
    redis_client.set(f"result_{session_id}_boxed",  json.dumps(boxed_images), ex=3600)
    return "done"


@celery.task(name="tasks.cleanup_old_uploads")
def cleanup_old_uploads():
    """Delete uploaded files older than 24 hours from static/uploads/."""
    cutoff = time.time() - (24 * 3600)
    deleted = 0
    for filepath in glob.glob(os.path.join(UPLOAD_FOLDER, "*.jpg")):
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                deleted += 1
        except OSError:
            pass
    print(f"[cleanup] Removed {deleted} file(s) older than 24 hours")
    return deleted
