# 📚 FaceOS — Study Guide

> Everything you need to learn to fully understand this project, organized from fundamentals to advanced topics. Each section lists the concept, why it's used here, and what to study.

---

## 📋 Table of Contents

1. [Python Fundamentals](#1-python-fundamentals)
2. [Computer Vision & Face Recognition](#2-computer-vision--face-recognition)
3. [Machine Learning Concepts](#3-machine-learning-concepts)
4. [Flask Web Framework](#4-flask-web-framework)
5. [Databases — PostgreSQL & SQLAlchemy](#5-databases--postgresql--sqlalchemy)
6. [Vector Databases & pgvector](#6-vector-databases--pgvector)
7. [Redis](#7-redis)
8. [Celery — Async Task Queues](#8-celery--async-task-queues)
9. [Docker & Containers](#9-docker--containers)
10. [React & Frontend](#10-react--frontend)
11. [REST APIs & SSE](#11-rest-apis--sse)
12. [Security Best Practices](#12-security-best-practices)
13. [System Design](#13-system-design)
14. [Project File-by-File Breakdown](#14-project-file-by-file-breakdown)
15. [Learning Roadmap](#15-learning-roadmap)

---

## 1. Python Fundamentals

These are the core Python concepts used throughout the backend.

### What's used in this project
| Concept | Where used |
|---|---|
| `os.getenv()` | Reading environment variables (secrets, config) |
| `hashlib.sha256()` | Computing file hashes for deduplication |
| `uuid.uuid4()` | Generating unique filenames |
| `json.dumps / loads` | Serializing data for Redis |
| `glob.glob()` | Finding files for cleanup task |
| `os.path.getmtime()` | Checking file age for cleanup |
| Generator functions (`yield`) | SSE streaming response |
| Decorators (`@app.route`, `@celery.task`) | Flask routes & Celery tasks |
| Context managers (`with`) | Flask app context, file handling |
| List comprehensions | NMS filtering, album building |

### Study topics
- **Python generators** — how `yield` works, why they're memory-efficient
- **Decorators** — `@` syntax, how `@app.route` registers URL handlers
- **Environment variables** — `os.environ`, `os.getenv()`, why secrets shouldn't be hardcoded
- **`hashlib`** — SHA-256, MD5, what a hash is and why it's one-way
- **`uuid`** — what UUIDs are, UUID4 (random), UUID1 (time-based)

### Resources
- [Python Official Docs](https://docs.python.org/3/)
- [Real Python — Generators](https://realpython.com/introduction-to-python-generators/)
- [Real Python — Decorators](https://realpython.com/primer-on-python-decorators/)

---

## 2. Computer Vision & Face Recognition

The core AI pipeline of this project.

### Pipeline overview
```
Image → Face Detection → Crop face → Extract embedding → Compare embeddings → Identity
```

### Key concepts

#### Face Detection (RetinaFace)
- **What it does**: Locates faces in an image and returns bounding boxes `{x, y, w, h}`
- **How it works**: Deep CNN trained to output face regions + facial landmarks (eyes, nose, mouth)
- **Output**: List of bounding boxes with confidence scores
- **Study**: Anchor-based object detection, sliding windows, CNN feature maps

#### Face Embedding (ArcFace)
- **What it does**: Converts a cropped face image into a 512-dimensional numerical vector
- **Key property**: Same person → vectors close together. Different people → vectors far apart
- **Why ArcFace**: Uses "Additive Angular Margin Loss" — better separation between identities than older models like VGG-Face
- **Study**: CNNs, feature extraction, embedding spaces, loss functions

#### Distance-based Recognition
```python
# Euclidean distance between two 512-dim vectors
distance = sqrt(sum((a_i - b_i)^2 for i in range(512)))
# Close distance (< threshold) = same person
```
- **L2 distance** (Euclidean): straight-line distance in high-dimensional space
- **Cosine similarity**: angle between vectors (alternative to L2)
- **Threshold**: if distance < 0.8, it's a match

#### Non-Maximum Suppression (NMS)
- **Problem**: RetinaFace sometimes detects the same face twice with slightly different boxes
- **Solution**: Calculate IoU (Intersection over Union) between boxes. If two boxes overlap > 25%, keep only the larger one
- **IoU formula**: `overlap_area / (area_A + area_B - overlap_area)`

#### DBSCAN Clustering
- **What it does**: Groups unknown faces by identity without knowing how many people there are
- **How it works**: Finds dense clusters of points in embedding space. Points far from any cluster = noise (-1)
- **Parameters**: `eps` (max distance to be in same cluster), `min_samples` (min points to form cluster)
- **Why not K-Means**: K-Means requires knowing K (number of clusters) upfront. DBSCAN doesn't.

### Libraries
| Library | Role |
|---|---|
| `deepface` | High-level wrapper around ArcFace + RetinaFace |
| `opencv-python` | Image reading, resizing, drawing bounding boxes |
| `numpy` | Vector math (L2 normalization, array operations) |
| `scikit-learn` | DBSCAN implementation |
| `pillow` | Image format conversion, EXIF rotation |
| `pillow-heif` | HEIC (iPhone) image support |

### Study topics
- **Convolutional Neural Networks (CNNs)**: filters, feature maps, pooling
- **Transfer learning**: using pre-trained model weights for a new task
- **Embedding spaces**: how high-dimensional vectors represent semantic meaning
- **ArcFace paper**: [ArcFace: Additive Angular Margin Loss for Deep Face Recognition](https://arxiv.org/abs/1801.07698)
- **DBSCAN**: [Scikit-learn DBSCAN docs](https://scikit-learn.org/stable/modules/clustering.html#dbscan)

---

## 3. Machine Learning Concepts

### What's used

#### L2 Normalization
```python
X = X / np.linalg.norm(X, axis=1, keepdims=True)
```
Divides each vector by its magnitude, projecting it onto a unit sphere. Makes distance comparisons fair regardless of vector scale.

#### Confidence Scoring
```python
confidence = max(0.0, 1.0 - (distance / 2.0))
```
Converts a raw distance (0 = identical, 2 = completely opposite) into a 0–1 confidence score.

#### Dual-Threshold Matching
```python
# Match only if:
# 1. Best match distance is below threshold
# 2. Gap between best and second-best is big enough (margin)
```
Prevents false positives when the best match is still not confident enough (e.g., person not in DB).

### Study topics
- **Euclidean distance vs cosine similarity** — when to use each
- **Precision vs Recall** — tradeoff in face recognition thresholds
- **False positives / False negatives** — impact on recognition accuracy
- **Hyperparameter tuning** — how threshold and margin affect results

---

## 4. Flask Web Framework

The Python backend API server.

### What's used

#### Route definitions
```python
@app.route("/upload_stream", methods=["POST"])
def upload_stream():
    ...
```

#### Request handling
```python
files = request.files.getlist("images")   # multipart file upload
body  = request.json                       # JSON body
```

#### Response types
```python
return jsonify({"status": "ok"})           # JSON response
return Response(generate(), mimetype="text/event-stream")  # SSE stream
```

#### Flask-CORS
Allows the React frontend (port 5173) to call the Flask API (port 5000) — browsers block cross-origin requests by default.

#### Flask-Session
Stores session data server-side in Redis instead of in a browser cookie. Needed because session data is too large for a cookie.

#### Error handlers
```python
@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large"}), 413
```

### Study topics
- [Flask Official Docs](https://flask.palletsprojects.com/)
- **HTTP methods** — GET, POST, DELETE, PATCH and when to use each
- **Status codes** — 200, 201, 400, 404, 409, 413, 500, 503
- **CORS** — why browsers enforce same-origin policy and how CORS headers work
- **Sessions & cookies** — stateless HTTP, session ID in cookie, server-side storage

---

## 5. Databases — PostgreSQL & SQLAlchemy

### PostgreSQL
- **Relational database** — data stored in tables with rows and columns
- **Used for**: storing persons, image metadata, face embeddings
- **`pgvector` extension**: adds a `vector` column type for ML embeddings

### SQLAlchemy (ORM)
Object-Relational Mapper — maps Python classes to database tables.

```python
class Person(db.Model):
    __tablename__ = "persons"
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # Relationship — one person → many face embeddings
    faces = db.relationship("FaceEmbedding", backref="person", cascade="all, delete-orphan")
```

### Schema (3 tables)
```
persons              images                    face_embeddings
─────────────────    ──────────────────────    ──────────────────────────────
id (PK)              id (PK)                   id (PK)
name                 filename (UUID)            person_id (FK → persons)
created_at           original_name             image_id (FK → images)
                     filepath                  embedding (Vector 512)
                     file_hash (SHA-256)       bounding_box (JSONB)
                     created_at                confidence
                                               created_at
```

### Raw SQL used
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add column to existing table (safe migration)
ALTER TABLE images ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);

-- Create ANN search index
CREATE INDEX IF NOT EXISTS face_emb_ivfflat_idx
ON face_embeddings USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);
```

### Study topics
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)
- **Primary keys, Foreign keys, Relationships** (one-to-many, many-to-many)
- **`CASCADE`** — what happens to child rows when parent is deleted
- **JSONB** — storing JSON in PostgreSQL, when to use vs separate columns
- **Indexes** — why they speed up queries, B-tree vs IVFFlat
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)

---

## 6. Vector Databases & pgvector

### The problem
Comparing a new face embedding against 10,000 stored embeddings with brute force = 10,000 distance calculations every recognition. Too slow at scale.

### The solution: Approximate Nearest Neighbor (ANN)
Instead of checking every vector, build an index that lets you find the closest vectors in O(log N) time.

### IVFFlat Index
```sql
CREATE INDEX face_emb_ivfflat_idx
ON face_embeddings USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);
```
- **IVF** = Inverted File Index
- **Flat** = flat (exact) comparison within each cluster
- **lists = 100** = divide all vectors into 100 clusters (Voronoi cells). At query time, search only the nearest clusters.
- **Tradeoff**: slightly approximate but >10x faster than brute force

### pgvector query
```sql
SELECT person_id, embedding <-> '[0.1, 0.3, ...]'::vector AS distance
FROM face_embeddings
ORDER BY distance
LIMIT 5;
```
`<->` is the L2 distance operator added by pgvector.

### Study topics
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- **Vector similarity search** — L2 distance, cosine similarity, dot product
- **HNSW vs IVFFlat** — two common ANN index types
- **Curse of dimensionality** — why high-dimensional spaces are hard
- [Pinecone Learning Center](https://www.pinecone.io/learn/) — great intro to vector DBs

---

## 7. Redis

An in-memory key-value store. Used for 4 different things in this project.

### 4 uses in this project

| Use | Key pattern | TTL | How |
|---|---|---|---|
| **Flask sessions** | `flask_session:<id>` | Browser session | Flask-Session |
| **Celery broker** | Celery internal keys | Auto-managed | Celery config |
| **SSE pub/sub** | `progress_<session_id>` | Per scan | `redis.pubsub()` |
| **Result cache** | `result_<sid>_albums` | 1 hour | `redis.set(..., ex=3600)` |

### Pub/Sub pattern (used for SSE)
```python
# Worker publishes progress updates
redis_client.publish("progress_abc123", json.dumps({"type": "progress", "step": 1}))

# Flask subscribes and streams to browser
pubsub = redis_client.pubsub()
pubsub.subscribe("progress_abc123")
for message in pubsub.listen():
    yield f"data: {message['data']}\n\n"
```

### Study topics
- [Redis University (free)](https://university.redis.com/)
- **Redis data types**: String, List, Hash, Set, Sorted Set, Pub/Sub
- **TTL (Time-To-Live)**: automatic key expiry
- **In-memory vs persistent**: Redis is RAM-first, optional disk persistence
- **Pub/Sub**: publish-subscribe messaging pattern

---

## 8. Celery — Async Task Queues

### The problem
DeepFace takes 5–30 seconds per image. If Flask waits for it, the browser times out and only 1 user can upload at a time.

### The solution
```
Browser → Flask (instant response) → Redis queue → Celery worker (background)
                ↑                                          ↓
                └─────────── SSE progress events ─────────┘
```

### Key concepts

#### Task definition
```python
@celery.task(name="tasks.process_uploaded_images_task")
def process_uploaded_images_task(session_id, files_data, threshold, margin):
    # This runs in the worker process, not the Flask server
    ...
```

#### Task dispatch
```python
# Non-blocking — returns immediately
tasks.process_uploaded_images_task.delay(session_id, saved_files_data, ...)
```

#### Flask app context in workers
```python
class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():          # gives worker access to db, config
            return self.run(*args, **kwargs)
celery.Task = ContextTask
```

#### Celery Beat (scheduler)
```python
celery.conf.beat_schedule = {
    "cleanup-old-uploads": {
        "task": "tasks.cleanup_old_uploads",
        "schedule": 3600.0,  # every hour
    }
}
```

### Study topics
- [Celery Docs](https://docs.celeryq.dev/)
- **Message brokers** — Redis vs RabbitMQ, what a broker does
- **Worker concurrency** — prefork vs eventlet vs gevent, why we use prefork=2
- **Task retries** — `autoretry_for`, `max_retries`, `countdown`
- **Idempotency** — why tasks should be safe to run twice

---

## 9. Docker & Containers

### Core concepts

#### What is a container?
A lightweight, isolated process with its own filesystem, networking, and dependencies. Like a VM but shares the host OS kernel — starts in milliseconds, not minutes.

#### Dockerfile (Python backend)
```dockerfile
FROM python:3.10-slim          # base image
WORKDIR /app                   # working directory inside container
RUN apt-get install ...        # system dependencies
COPY requirements.txt .        # copy just requirements first (layer caching)
RUN pip install -r requirements.txt
COPY . .                       # then copy source code
CMD ["gunicorn", ...]          # default command
```

**Why copy requirements first?** Docker builds in layers. If requirements.txt hasn't changed, it uses cached layer and skips `pip install` — much faster rebuilds.

#### docker-compose.yml
Defines and links multiple containers as one application:
```yaml
services:
  db:      # PostgreSQL
  redis:   # Redis
  web:     # Flask API (Gunicorn)
  worker:  # Celery worker
  beat:    # Celery scheduler
  frontend: # React + Vite
```

#### Volumes
```yaml
volumes:
  - pgdata:/var/lib/postgresql/data  # named volume — persists DB data between restarts
  - .:/app                           # bind mount — live code sync for development
```

#### Health checks
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U user -d facedb"]
  interval: 5s
  retries: 5
```
Ensures dependent services (web, worker) wait until the DB is actually ready — not just started.

#### .dockerignore
Like `.gitignore` but for Docker build context. Prevents `node_modules/`, `.env`, `__pycache__/` from being sent to the Docker daemon — makes builds faster and images smaller.

### Study topics
- [Docker Official Tutorial](https://docs.docker.com/get-started/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- **Images vs containers** — image = blueprint, container = running instance
- **Port mapping** — `"5000:5000"` means host:container
- **Networks** — Docker Compose creates a private network; services talk by service name (e.g., `db`, `redis`)
- **Layer caching** — how Docker reuses build layers

---

## 10. React & Frontend

### Core React concepts used

#### State management
```jsx
const [files, setFiles]     = useState([]);      // uploaded files
const [albums, setAlbums]   = useState(null);    // recognition results
const [toasts, setToasts]   = useState([]);      // notifications
```

#### Side effects
```jsx
useEffect(() => {
    fetchPersons();          // runs once on mount
}, []);
```

#### Callbacks
```jsx
const toast = useCallback((msg, type = 'success') => {
    // memoized so it doesn't re-create on every render
}, []);
```

#### SSE (Server-Sent Events) client
```jsx
const res = await fetch(`${API}/upload_stream`, { method: 'POST', body: form });
const reader = res.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // parse SSE chunks and update UI
}
```

#### Component composition
```jsx
// AlbumCard is a reusable component
{Object.entries(albums).map(([person, images], idx) => (
    <AlbumCard key={person} person={person} images={images} idx={idx} ... />
))}
```

### Vite
- **Dev server**: instant HMR (Hot Module Replacement) — changes reflect in <100ms
- **Bundler**: uses Rolldown/esbuild, much faster than Webpack
- **ESM-first**: uses native ES modules in development

### Study topics
- [React Official Docs](https://react.dev/)
- **useState, useEffect, useCallback, useRef** — the four hooks used in this project
- **Props vs State** — what each is for
- **Lifting state up** — why state lives in the parent (App) and is passed down
- **Fetch API** — `fetch()`, `async/await`, handling responses
- [Vite Docs](https://vitejs.dev/)
- **CSS custom properties (variables)** — `--accent`, `--glass-bg` etc.
- **Glassmorphism** — `backdrop-filter: blur()`, translucent backgrounds

---

## 11. REST APIs & SSE

### REST API design
| Pattern | This project |
|---|---|
| Noun-based URLs | `/persons`, `/upload_stream` |
| HTTP verbs for actions | GET list, POST create, POST delete (could be DELETE) |
| JSON request/response | `Content-Type: application/json` |
| Appropriate status codes | 200, 400, 404, 409, 413, 503 |

### Server-Sent Events (SSE)
A one-way stream from server → browser over a regular HTTP connection.

**Server (Flask):**
```python
def generate():
    pubsub.subscribe("progress_abc")
    for message in pubsub.listen():
        yield f"data: {json.dumps(data)}\n\n"  # SSE format: "data: ...\n\n"

return Response(generate(), mimetype="text/event-stream")
```

**Client (React):**
```javascript
const reader = res.body.getReader();
// reads chunks as they arrive
```

**Why SSE instead of WebSockets?**
- SSE is simpler — one-directional, works over HTTP/1.1
- WebSockets need a separate upgrade handshake and bidirectional channel
- SSE auto-reconnects; built-in browser support via `EventSource`

### Gunicorn
```
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 300 --worker-class=gthread --threads=2 app:app
```
- `-w 2` — 2 worker processes
- `--worker-class=gthread` — each worker is multi-threaded (needed for SSE long-polling)
- `--threads=2` — 2 threads per worker = 4 concurrent connections total
- `--timeout 300` — SSE connections can stay open for up to 5 minutes

### Study topics
- [MDN — REST](https://developer.mozilla.org/en-US/docs/Glossary/REST)
- [MDN — Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- **HTTP/1.1 vs HTTP/2** — connection multiplexing
- **WSGI** — Python web server interface, how Gunicorn runs Flask

---

## 12. Security Best Practices

### What's implemented in this project

#### 1. Secret management via `.env`
```
SECRET_KEY=change-me-to-long-random-string
POSTGRES_PASSWORD=FaceAppSecure123
```
- Secrets never hardcoded in source code
- `.env` in `.gitignore` — never committed
- `.env.example` committed as a template

#### 2. Filename sanitization
```python
from werkzeug.utils import secure_filename
secure_name = secure_filename(original_name)    # removes path traversal chars
unique_name = f"{uuid.uuid4().hex}{ext}"        # UUID prevents collisions
```
Prevents attacks like uploading a file named `../../etc/passwd`.

#### 3. File size limits
```python
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB
```
Prevents DoS by huge uploads consuming disk/RAM.

#### 4. CORS configuration
```python
CORS(app, supports_credentials=True,
     origins=["http://localhost:5173"])  # whitelist, not wildcard *
```

#### 5. Server-side sessions
Sessions stored in Redis, not in the browser cookie (which could be tampered with).

### Study topics
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) — most common web vulnerabilities
- **Path traversal** — how `../` in filenames can escape upload directories
- **SQL injection** — why ORMs (SQLAlchemy) protect you
- **CSRF** — why `SESSION_USE_SIGNER=True` matters
- **Environment variables** — 12-factor app methodology

---

## 13. System Design

### Patterns used in this project

#### 1. Microservices
Each service has one responsibility: DB, cache, API, worker, scheduler, frontend. They communicate over a shared network.

#### 2. Producer-Consumer (Task Queue)
```
Flask (producer) → Redis queue → Celery worker (consumer)
```
Decouples the web server from heavy computation.

#### 3. Pub/Sub (Event-driven)
```
Worker publishes events → Redis channel → Flask subscribes → SSE to browser
```
Real-time updates without polling.

#### 4. Cache-aside
```
Redis cache miss → compute result → store in Redis → return
Redis cache hit  → return cached result immediately
```
Result cache with 1-hour TTL avoids recomputing on page refresh.

#### 5. Idempotency via content hashing
```
SHA-256(file) → check DB → already exists? reuse. New? process.
```
Makes uploads safe to retry.

#### 6. Separation of concerns
| Layer | Responsible for |
|---|---|
| `app.py` | HTTP routing, request/response |
| `tasks.py` | ML processing logic |
| `utils/database.py` | DB models and schema |
| `utils/deepface_utils.py` | Face detection/embedding |
| `utils/recognition.py` | Identity matching |
| `utils/clustering.py` | DBSCAN grouping |

### Study topics
- [System Design Primer (GitHub)](https://github.com/donnemartin/system-design-primer)
- **Horizontal vs vertical scaling**
- **CAP theorem** — Consistency, Availability, Partition tolerance
- **Message queues** — when to use vs direct API calls
- **The Twelve-Factor App** — methodology for building scalable services

---

## 14. Project File-by-File Breakdown

| File | What it does | Key concepts to study |
|---|---|---|
| `app.py` | Flask API server — all HTTP routes | Flask, CORS, sessions, SHA-256, SSE |
| `celery_app.py` | Creates the Celery instance | Celery factory pattern, broker config |
| `celery_worker.py` | Worker entrypoint | Flask app context, circular imports |
| `tasks.py` | Background image processing | Celery tasks, DBSCAN, SSE pub/sub |
| `utils/database.py` | DB models + init | SQLAlchemy ORM, pgvector, migrations |
| `utils/deepface_utils.py` | ArcFace embedding | DeepFace, NMS, IoU, face confidence |
| `utils/recognition.py` | Match face to person | pgvector ANN, dual-threshold |
| `utils/clustering.py` | Group unknown faces | DBSCAN, L2 normalization |
| `docker-compose.yml` | Orchestrate 6 services | Docker Compose, healthchecks, volumes |
| `Dockerfile` | Python image | Docker layering, apt, pip |
| `frontend/src/App.jsx` | Entire React UI | React hooks, SSE client, fetch API |
| `frontend/src/App.css` | Glassmorphism UI | CSS variables, backdrop-filter, animations |
| `.env.example` | Config template | 12-factor app, secret management |
| `.gitignore` | Git exclusions | What not to commit and why |
| `README.md` | Project documentation | Technical writing |

---

## 15. Learning Roadmap

### 🟢 Beginner (start here)
1. **Python basics** — functions, classes, lists, dicts
2. **HTTP basics** — what is a request/response, JSON, status codes
3. **Flask** — make a simple API with 2–3 routes
4. **React basics** — components, props, useState, useEffect
5. **Git** — commit, push, pull, branches

### 🟡 Intermediate (next)
6. **PostgreSQL** — CREATE TABLE, SELECT, JOIN, foreign keys
7. **SQLAlchemy** — models, relationships, queries
8. **Docker** — build an image, run a container, write a Dockerfile
9. **REST API design** — verbs, status codes, JSON conventions
10. **Redis basics** — SET, GET, TTL, Pub/Sub

### 🔴 Advanced (after intermediate)
11. **Machine learning** — how CNNs work, what embeddings are
12. **Celery** — tasks, brokers, workers, beat scheduler
13. **Docker Compose** — multi-service apps, networking, volumes
14. **Vector databases** — ANN search, IVFFlat, HNSW
15. **System design** — scalability, message queues, caching patterns

### Suggested project progression
1. → Build a Flask + PostgreSQL CRUD API (no ML)
2. → Add Celery + Redis for a background email sender
3. → Containerize it with Docker Compose
4. → Add a React frontend
5. → Add ML (start with a pre-trained image classifier)
6. → Swap classifier for face recognition (this project!)

---

*Made for learning. Every line in this project is intentional — follow the code, understand the why, and you'll understand the whole stack.*
