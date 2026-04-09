import os
import cv2
from PIL import Image
import pillow_heif
from flask import Flask, request, session, jsonify
from flask_cors import CORS

from utils.deepface_utils import get_faces_data  # 👈 NEW (with boxes)
from utils.clustering import cluster_faces
from utils.recognition import load_known_faces, find_person
from utils.embedding_store import load_embeddings, save_embeddings

app = Flask(__name__)
app.secret_key = "supersecretkey123"
# Enable cookies for sessions and allow standard React dev server ports
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"])

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def index():
    if "albums" in session:
        return jsonify({"has_session": True, "albums": session["albums"], "boxed_image": session.get("boxed_image")})
    return jsonify({"has_session": False})


@app.route("/upload", methods=["POST"])
def upload():
    print("Upload route triggered")

    files = request.files.getlist("images")

    all_embeddings = []
    image_paths = []
    names = []
    confidences = []
    boxes = []

    known_faces = load_known_faces()

    for file in files:
        filename = file.filename.replace(" ", "_")
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)

# 🔥 HANDLE HEIC
        if path.lower().endswith(".heic"):
            heif_file = pillow_heif.read_heif(path)
            image = Image.frombytes(
              heif_file.mode,
              heif_file.size,
              heif_file.data,
              "raw"
            )

            new_path = path.replace(".heic", ".jpg")
            image.save(new_path, "JPEG")

            path = new_path  # 👈 use converted file

        print("Saved:", path)

        # 🔥 get faces (embedding + box)
        faces = get_faces_data(path)

        for face in faces:
            emb = face["embedding"]
            box = face["box"]

            name, confidence = find_person(emb, known_faces)

            all_embeddings.append(emb)
            image_paths.append(file.filename)
            names.append(name)
            confidences.append(confidence)
            boxes.append(box)

        # 🔥 DRAW BOUNDING BOXES
        img = cv2.imread(path)

        if img is None:
           print("❌ ERROR: Image not loaded:", path)
           continue

        for name, conf, box in zip(names, confidences, boxes):
            x, y, w, h = box["x"], box["y"], box["w"], box["h"]

            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

            label = f"{name} ({round(conf, 2)})"
            cv2.putText(img, label, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 255, 0), 2)

        boxed_filename = "boxed_" + filename
        boxed_path = os.path.join(app.config["UPLOAD_FOLDER"], boxed_filename)
        cv2.imwrite(boxed_path, img)

    # 🔹 clustering
    labels = cluster_faces(all_embeddings)
    labels = [int(label) for label in labels]

    # 🔥 albums
    albums = {}

    for img, name, conf in zip(image_paths, names, confidences):

        if name not in albums:
            albums[name] = []

        albums[name].append({
            "image": img,
            "confidence": round(conf, 3)
        })

    print("Albums:", albums)

    # 🔥 save session
    session["albums"] = albums
    if 'boxed_filename' in locals():
        session["boxed_image"] = boxed_filename
    else:
        session["boxed_image"] = None

    return jsonify({
        "albums": albums,
        "boxed_image": session.get("boxed_image")
    })


@app.route("/add_person", methods=["POST"])
def add_person():
    req = request.json or {}
    name = req.get("name")
    image = req.get("image")

    if not name or not image:
        return jsonify({"error": "Invalid input"}), 400

    image_path = os.path.join("static/uploads", image)

    faces = get_faces_data(image_path)

    if not faces:
        return jsonify({"error": "No face found"}), 400

    data = load_embeddings()

    name = name.lower()

    # 🔥 check if new or existing
    is_new_person = name not in data

    if is_new_person:
        data[name] = []

    # add embeddings
    for face in faces:
        data[name].append(face["embedding"])

    save_embeddings(data)

    print(f"Saved embeddings for {name}. Total: {len(data[name])}")

    # 🔥 DIFFERENT MESSAGES
    msg = f'🆕 Created new person "{name}" and added face!' if is_new_person else f'➕ Added another image to "{name}"'
    return jsonify({"success": True, "message": msg})


@app.route("/reset", methods=["POST"])
def reset():
    session.pop("albums", None)
    session.pop("boxed_image", None)
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True)