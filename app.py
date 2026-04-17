import os
import json
import uuid
import hashlib
from flask import Flask, Response, jsonify, request, session
from flask_cors import CORS
from flask_session import Session
from werkzeug.utils import secure_filename
import redis
import pillow_heif
from PIL import Image, ImageOps
from sqlalchemy import text

from celery_app import celery
from utils.database import db, init_db, Person, ImageRecord, FaceEmbedding

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey123")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Flask-Session via Redis (not cookies)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.from_url(REDIS_URL)
Session(app)

# PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/facedb"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
init_db(app)

# 50 MB upload limit
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Wire Flask app context into every Celery task execution
class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask

CORS(
    app,
    supports_credentials=True,
    origins=["http://localhost:5173", "http://localhost:3000",
             "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

CONFIDENCE_THRESHOLD = float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "0.8"))
MARGIN_THRESHOLD     = float(os.getenv("FACE_MARGIN_THRESHOLD", "0.05"))

redis_client = redis.from_url(REDIS_URL)

# Import tasks AFTER celery + context are configured
import tasks


# ── Helpers ────────────────────────────────────────────────────────────────────
def _to_jpg(path: str) -> str:
    if path.lower().endswith(".heic"):
        heif_file = pillow_heif.read_heif(path)
        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
    else:
        img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    out = os.path.splitext(path)[0] + ".jpg"
    img.save(out, "JPEG", quality=95)
    return out


def _sha256(file_obj) -> str:
    """Compute SHA-256 of an open file object, then rewind it."""
    h = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(8192), b""):
        h.update(chunk)
    file_obj.seek(0)
    return h.hexdigest()


# ── Error handlers ─────────────────────────────────────────────────────────────
@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large. Maximum upload size is 50 MB per file."}), 413


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    status = {"status": "ok", "redis": False, "db": False}
    try:
        redis_client.ping()
        status["redis"] = True
    except Exception:
        pass
    try:
        db.session.execute(text("SELECT 1"))
        status["db"] = True
    except Exception:
        pass
    code = 200 if (status["redis"] and status["db"]) else 503
    return jsonify(status), code


@app.route("/")
def index():
    if "session_id" in session:
        sid = session["session_id"]
        albums = redis_client.get(f"result_{sid}_albums")
        boxed  = redis_client.get(f"result_{sid}_boxed")
        if albums and boxed:
            return jsonify({
                "has_session": True,
                "albums": json.loads(albums),
                "boxed_images": json.loads(boxed),
            })
    return jsonify({"has_session": False})


@app.route("/upload_stream", methods=["POST"])
def upload_stream():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "No files"}), 400

    session_id = str(uuid.uuid4())
    session["session_id"] = session_id

    saved_files_data = []

    for file in files:
        if file.filename == '':
            continue

        # Hash before saving so we can dedup
        file_hash = _sha256(file)

        original_name = file.filename
        secure_name   = secure_filename(original_name)
        ext           = os.path.splitext(secure_name)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        raw_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)

        file.save(raw_path)

        try:
            raw_path        = _to_jpg(raw_path)
            unique_filename = os.path.basename(raw_path)
        except Exception as e:
            print(f"[warn] conversion failed for {original_name}: {e}")

        saved_files_data.append({
            "original_name": original_name,
            "filename":      unique_filename,
            "filepath":      raw_path,
            "file_hash":     file_hash,
        })

    tasks.process_uploaded_images_task.delay(
        session_id, saved_files_data, CONFIDENCE_THRESHOLD, MARGIN_THRESHOLD
    )

    def generate():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"progress_{session_id}")
        for message in pubsub.listen():
            if message['type'] == 'message':
                data_str = message['data'].decode('utf-8')
                data = json.loads(data_str)
                yield f"data: {data_str}\n\n"
                if data.get('type') == 'done':
                    break

    return Response(
        generate(), mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/persons", methods=["GET"])
def list_persons():
    persons = Person.query.all()
    return jsonify({"persons": [{"name": p.name, "face_count": len(p.faces)} for p in persons]})


@app.route("/add_person", methods=["POST"])
def add_person():
    req   = request.json or {}
    name  = req.get("name", "").strip().lower()
    image = req.get("image", "").strip()

    if not name or not image:
        return jsonify({"error": "name and image are required"}), 400

    img_record = ImageRecord.query.filter_by(filename=image).first()
    if not img_record:
        return jsonify({"error": f"Image not found in database: {image}"}), 404

    person = Person.query.filter_by(name=name).first()
    is_new = False
    if not person:
        person = Person(name=name)
        db.session.add(person)
        db.session.commit()
        is_new = True

    faces = FaceEmbedding.query.filter_by(image_id=img_record.id).all()
    if not faces:
        return jsonify({"error": "No face detected in image"}), 400

    for face in faces:
        face.person_id = person.id
    db.session.commit()

    msg = (f'Created "{name}" with {len(faces)} face(s).' if is_new
           else f'Added {len(faces)} face(s) to "{name}".')
    return jsonify({"success": True, "message": msg, "is_new": is_new})


@app.route("/delete_person", methods=["POST"])
def delete_person():
    name = (request.json or {}).get("name", "").strip().lower()
    if not name:
        return jsonify({"error": "name is required"}), 400

    person = Person.query.filter_by(name=name).first()
    if not person:
        return jsonify({"error": f'"{name}" not found'}), 404

    db.session.delete(person)
    db.session.commit()
    return jsonify({"success": True, "message": f'Deleted "{name}"'})


@app.route("/rename_person", methods=["POST"])
def rename_person():
    body     = request.json or {}
    old_name = body.get("old_name", "").strip().lower()
    new_name = body.get("new_name", "").strip().lower()

    if not old_name or not new_name:
        return jsonify({"error": "old_name and new_name required"}), 400

    person = Person.query.filter_by(name=old_name).first()
    if not person:
        return jsonify({"error": f'"{old_name}" not found'}), 404

    if Person.query.filter_by(name=new_name).first():
        return jsonify({"error": f'"{new_name}" already exists'}), 409

    person.name = new_name
    db.session.commit()
    return jsonify({"success": True})


@app.route("/settings", methods=["GET", "POST"])
def settings():
    global CONFIDENCE_THRESHOLD, MARGIN_THRESHOLD
    if request.method == "POST":
        body = request.json or {}
        if "confidence_threshold" in body:
            CONFIDENCE_THRESHOLD = float(body["confidence_threshold"])
        if "margin_threshold" in body:
            MARGIN_THRESHOLD = float(body["margin_threshold"])
    return jsonify({"confidence_threshold": CONFIDENCE_THRESHOLD,
                    "margin_threshold": MARGIN_THRESHOLD})


@app.route("/reset", methods=["POST"])
def reset():
    sid = session.pop("session_id", None)
    if sid:
        redis_client.delete(f"result_{sid}_albums")
        redis_client.delete(f"result_{sid}_boxed")
    return jsonify({"success": True})


if __name__ == "__main__":
    # Dev only — Docker uses Gunicorn
    app.run(debug=True, threaded=True, host="0.0.0.0")
