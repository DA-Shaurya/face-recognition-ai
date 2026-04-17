# 🧠 FaceOS — Production-Grade Face Recognition Platform

![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![React](https://img.shields.io/badge/React-19.x-61DAFB.svg)
![DeepFace](https://img.shields.io/badge/DeepFace-ArcFace-orange.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20+%20pgvector-336791.svg)
![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)
![Celery](https://img.shields.io/badge/Celery-5.4-37814A.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

A production-ready, fully containerized face recognition platform. Upload photos, auto-detect every face using **ArcFace + RetinaFace**, group unknown people into smart clusters, tag identities, and recognize known people in future uploads — all powered by a scalable microservices architecture.

---

## ✨ Feature Overview

### 🔬 AI & Recognition
| Feature | Details |
|---|---|
| **ArcFace Model** | State-of-the-art face embedding model (512-dim vectors) replacing legacy VGG-Face. More accurate under occlusion and variable lighting. |
| **RetinaFace Detector** | High-precision face detector with sub-pixel localization. |
| **pgvector ANN Search** | Approximate Nearest Neighbor search via an IVFFlat index on PostgreSQL. O(log N) recognition against millions of stored faces. |
| **Smart Confidence Scoring** | L2 distance converted to a 0–1 confidence score. Dual-threshold (distance + margin gap) to minimize false positives. |
| **DBSCAN Clustering** | Unknown faces across a batch of images are automatically grouped by identity into `Unknown #1`, `Unknown #2`, etc. allowing bulk-labeling. |
| **Non-Maximum Suppression** | Custom IoU-based NMS deduplicates overlapping detections from the same face. |
| **Minimum Face Size Filter** | Tiny background faces (< `MIN_FACE_PX` pixels) are filtered out before processing, preventing false positives from crowd scenes. |

### ⚙️ Backend Architecture
| Feature | Details |
|---|---|
| **Async Task Queue** | Heavy DeepFace/ML processing is offloaded to **Celery** workers. The Flask API returns instantly. |
| **Real-time SSE Progress** | Upload endpoint streams Server-Sent Events to the frontend as each image is processed, showing live progress. |
| **SHA-256 Deduplication** | Each uploaded file is hashed before saving. Re-uploading the same image skips re-processing and reuses existing DB records. |
| **Gunicorn WSGI Server** | Flask runs under Gunicorn (2 workers, gthread mode) instead of the dev server — production-safe. |
| **Celery Beat Scheduler** | A dedicated scheduler container runs a file cleanup job every hour, removing uploads older than 24 hours. |
| **Redis Session Storage** | Flask sessions stored server-side in Redis instead of cookies. Handles large session payloads and is stateless across workers. |
| **Result Caching** | Scan results (albums + annotated images) are cached in Redis for 1 hour so refreshing the page restores the last session. |
| **File Security** | All uploads are sanitized with `werkzeug.secure_filename()` and renamed to a UUID4 hex string, preventing path traversal and filename conflicts. |
| **50 MB Upload Limit** | Flask enforces `MAX_CONTENT_LENGTH = 50 MB` with a clean JSON 413 error response. |
| **HEIC Support** | iPhone HEIC photos are automatically converted to JPEG before processing using `pillow-heif`. |
| **EXIF Auto-rotation** | Photos are auto-rotated based on EXIF orientation metadata before analysis. |
| **Health Endpoint** | `GET /health` checks Redis ping + DB connectivity and returns `{"status":"ok","redis":true,"db":true}` or HTTP 503. |

### 🗄️ Data Storage
| Layer | Technology | What's Stored |
|---|---|---|
| **Vector DB** | PostgreSQL 16 + pgvector | 512-dim ArcFace embeddings with IVFFlat ANN index |
| **Relational DB** | SQLAlchemy ORM | `persons`, `images`, `face_embeddings` tables with foreign keys |
| **Cache / Broker** | Redis 7 | Session data, Celery task queue, SSE pub/sub, result cache |
| **File Storage** | Local filesystem | UUID-named JPEGs in `static/uploads/` |

### 🖥️ Frontend
| Feature | Details |
|---|---|
| **React 19 + Vite 8** | Fast HMR development server with ESM-first bundling. |
| **Drag & Drop Upload** | Drop zone supports JPG, PNG, HEIC, WEBP. Multiple files at once. |
| **Live Progress Bar** | SSE-powered progress indicator shows which file is currently being scanned. |
| **Face Albums View** | Results grouped by identity. Known people show an average confidence bar. |
| **Album Pagination** | Each identity album shows 12 images per page with Prev/Next navigation — no browser freeze on large batches. |
| **Annotated Preview** | Side-by-side view of the original and the annotated image with colored bounding boxes and name labels. |
| **Inline Tag / Correct** | Tag an unknown face or correct a misidentification directly from the results card. |
| **Rename Person** | Inline ✏️ edit button on each person row in the Persons DB view — calls `POST /rename_person`. |
| **Delete Person** | Remove a person and all their face embeddings from the database. |
| **Persons Database View** | Lists all known identities with their embedding count. |
| **Recognition Parameter Tuning** | Live sliders for confidence threshold and match margin, applied to the backend via `POST /settings`. |
| **Toast Notifications** | Success/error toasts for all actions with auto-dismiss. |
| **Session Persistence** | Refreshing the page restores the last scan from the Redis cache. |
| **Reset Session** | One-click reset clears the session and returns to the upload view. |

---

## 🏗️ Architecture

```
Browser (React + Vite)
    │
    │  HTTP / SSE
    ▼
Flask API (Gunicorn, 2 workers)
    │
    ├── Redis ──── Flask-Session storage
    │         ──── SSE pub/sub channel
    │         ──── Celery broker & result backend
    │         ──── Scan result cache (1h TTL)
    │
    ├── PostgreSQL (pgvector)
    │       ├── persons table
    │       ├── images table  (SHA-256 hash for dedup)
    │       └── face_embeddings table (512-dim Vector + IVFFlat index)
    │
    └── Celery Task ──► Worker (2 concurrent, prefork)
                              │
                              ├── DeepFace (ArcFace + RetinaFace)
                              ├── NMS + size filter
                              ├── pgvector ANN similarity search
                              ├── DBSCAN clustering (unknowns)
                              └── OpenCV bounding box drawing

Celery Beat ──► cleanup_old_uploads (every hour)
```

---

## 📂 Project Structure

```
face-recognition-app/
├── .env                        # Secrets & config (NOT committed to git)
├── .env.example                # Template — copy to .env to get started
├── .dockerignore
├── .gitignore
├── docker-compose.yml          # Orchestrates all 6 services
├── Dockerfile                  # Python backend image
│
├── app.py                      # Flask API — routes, session, Celery wiring
├── celery_app.py               # Standalone Celery factory (broker/backend config)
├── celery_worker.py            # Worker entrypoint — wires Flask app context
├── tasks.py                    # Celery tasks: image processing + file cleanup
├── requirements.txt
│
├── utils/
│   ├── database.py             # SQLAlchemy models + init_db (pgvector index)
│   ├── deepface_utils.py       # ArcFace embedding + NMS + size filter
│   ├── recognition.py          # pgvector ANN search + dual-threshold matching
│   └── clustering.py          # DBSCAN for unknown face grouping
│
├── static/
│   └── uploads/               # UUID-named JPEGs + boxed_ annotated copies
│
└── frontend/                  # React 19 + Vite 8 SPA
    ├── Dockerfile              # Node 20 Alpine image
    ├── .dockerignore
    ├── src/
    │   ├── App.jsx             # Main app — all views + components
    │   ├── App.css             # Glassmorphism dark theme
    │   └── main.jsx
    └── package.json
```

---

## 🐳 Quick Start (Docker — Recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone the repository
```bash
git clone https://github.com/DA-Shaurya/face-recognition-ai.git
cd face-recognition-app
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and set a strong SECRET_KEY and POSTGRES_PASSWORD
```

### 3. Start all services
```bash
docker compose up -d --build
```

This single command builds and starts **6 containers**:

| Container | Role | Port |
|---|---|---|
| `db` | PostgreSQL 16 + pgvector | 5432 |
| `redis` | Cache, broker, session store | 6379 |
| `web` | Flask API via Gunicorn | **5000** |
| `worker` | Celery task worker (concurrency=2) | — |
| `beat` | Celery periodic scheduler | — |
| `frontend` | React 19 + Vite dev server | **5173** |

### 4. Open the app
```
http://localhost:5173
```

### Useful commands
```bash
# View logs from all services live
docker compose logs -f

# View only worker logs (DeepFace output)
docker compose logs -f worker

# Check health
curl http://localhost:5000/health

# Stop everything (keep DB data)
docker compose down

# Stop and wipe database volume
docker compose down -v
```

---

## 🖥️ Local Development (Without Docker)

### Prerequisites
- Python 3.10
- Node.js 20+
- PostgreSQL 16 with pgvector extension
- Redis 7

### Backend
```bash
# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:password@localhost:5432/facedb
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=your-secret-key

# Start Flask dev server
python app.py

# In a separate terminal, start the Celery worker
celery -A celery_worker.celery worker --loglevel=info --concurrency=2

# In another terminal, start the Celery beat scheduler
celery -A celery_worker.celery beat --loglevel=info
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧠 How It Works

### Upload & Processing Pipeline

1. **Upload** — User drops images onto the React UI. The frontend `POST`s a `multipart/form-data` request to `/upload_stream`.

2. **Hashing** — Flask computes a SHA-256 hash of each file. If a file with that hash already exists in the DB, it is skipped (deduplication).

3. **Save** — Each file is renamed to a UUID hex string (e.g., `a3f91bc2...jpg`) via `werkzeug.secure_filename()` and saved to `static/uploads/`.

4. **Queue** — A Celery task `process_uploaded_images_task` is dispatched to the Redis broker. Flask immediately opens an SSE stream to the frontend.

5. **DeepFace** — The Celery worker runs `DeepFace.represent()` with the **ArcFace** model and **RetinaFace** detector on each image, extracting one 512-dimensional embedding per face.

6. **NMS + Size Filter** — Overlapping detections (IoU > 0.25) are deduplicated. Faces smaller than `MIN_FACE_PX` pixels are discarded (background crowd).

7. **Recognition** — Each embedding is compared against all known faces in PostgreSQL using pgvector's L2 distance (`<->` operator) with an IVFFlat ANN index. A match requires: `distance < threshold` AND `(second_distance - best_distance) > margin`.

8. **DBSCAN Clustering** — All "Unknown" faces in the batch are collected and clustered via DBSCAN. Each cluster becomes `Unknown #1`, `Unknown #2`, etc.

9. **Annotate** — OpenCV draws colored bounding boxes (green = known, blue = unknown) with name labels onto copies of each image (`boxed_<uuid>.jpg`).

10. **SSE Done Event** — The worker publishes a `done` event to Redis pub/sub. Flask forwards it to the browser. The React UI transitions to the Results view.

### Tagging a Person

1. Find the face in the Results view and type a name in the "Correct name…" input.
2. Click **Tag** — this calls `POST /add_person` with the filename and name.
3. Flask finds the `FaceEmbedding` rows for that image and links them to the named `Person` record.
4. Future uploads will now match against this embedding and return the person's name.

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check (Redis + DB) |
| `GET` | `/` | Check for active session / cached results |
| `POST` | `/upload_stream` | Upload images → returns SSE stream |
| `GET` | `/persons` | List all known persons |
| `POST` | `/add_person` | Tag a face as a named person |
| `POST` | `/delete_person` | Remove a person and their embeddings |
| `POST` | `/rename_person` | Rename an existing person |
| `GET/POST` | `/settings` | Get or update recognition thresholds |
| `POST` | `/reset` | Clear current session |

---

## ⚙️ Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `SECRET_KEY` | *(required)* | Flask session signing key |
| `FACE_CONFIDENCE_THRESHOLD` | `0.8` | Max L2 distance to count as a match |
| `FACE_MARGIN_THRESHOLD` | `0.05` | Min gap between best and 2nd-best match |
| `MIN_FACE_PX` | `80` | Minimum face bounding box size in pixels |
| `FLASK_ENV` | `development` | Set to `production` for live deployment |

---

## 🛠️ Tech Stack

### Backend
| Library | Version | Role |
|---|---|---|
| Flask | 3.0.3 | Web framework |
| Gunicorn | 22.0.0 | Production WSGI server |
| Celery | 5.4.0 | Async task queue |
| DeepFace | 0.0.91 | Face detection + embedding |
| TensorFlow | 2.16 | ArcFace model backend |
| RetinaFace | latest | Face detection sub-library |
| SQLAlchemy | 3.1.1 | ORM |
| psycopg2 | 2.9.9 | PostgreSQL driver |
| pgvector | 0.3.2 | Vector similarity extension |
| Redis-py | 5.0.3 | Redis client |
| Flask-Session | 0.8.0 | Server-side sessions |
| scikit-learn | 1.4.2 | DBSCAN clustering |
| OpenCV | 4.9 | Bounding box annotation |
| Pillow / pillow-heif | latest | HEIC conversion + EXIF rotation |
| NumPy | 1.26.4 | Vector math |
| Werkzeug | 3.0.2 | Secure filename, request utilities |

### Frontend
| Library | Version | Role |
|---|---|---|
| React | 19.2 | UI framework |
| Vite | 8.0 | Dev server + bundler |

### Infrastructure
| Service | Image | Role |
|---|---|---|
| PostgreSQL | `pgvector/pgvector:pg16` | Relational DB + vector search |
| Redis | `redis:7-alpine` | Cache, broker, sessions |
| Docker Compose | v2 | Container orchestration |

---

## 📝 License

MIT License — © 2026 Shaurya

---

*Built with ❤️ and a lot of neural network weights.*