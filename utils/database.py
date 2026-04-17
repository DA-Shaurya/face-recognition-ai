import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text

db = SQLAlchemy()


class Person(db.Model):
    __tablename__ = "persons"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    faces = db.relationship("FaceEmbedding", backref="person", cascade="all, delete-orphan")


class ImageRecord(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    # SHA-256 hash for deduplication
    file_hash = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    faces = db.relationship("FaceEmbedding", backref="image", cascade="all, delete-orphan")


class FaceEmbedding(db.Model):
    __tablename__ = "face_embeddings"
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=True)
    image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)
    # 512 dimensions for ArcFace
    embedding = db.Column(Vector(512), nullable=False)
    # {x, y, w, h}
    bounding_box = db.Column(JSONB, nullable=False)
    confidence = db.Column(db.Float, nullable=False, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_db(app):
    """Initialize database, create tables, and ensure indexes exist."""
    db.init_app(app)
    with app.app_context():
        # Enable pgvector extension (safe to call multiple times)
        try:
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.session.commit()
        except Exception:
            db.session.rollback()  # extension already exists — safe to continue

        # Create tables
        db.create_all()

        # Add file_hash column to images table if it doesn't exist yet
        try:
            db.session.execute(text(
                "ALTER TABLE images ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64)"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Create IVFFlat ANN index on embeddings for fast nearest-neighbor search
        try:
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS face_emb_ivfflat_idx
                ON face_embeddings USING ivfflat (embedding vector_l2_ops)
                WITH (lists = 100)
            """))
            db.session.commit()
        except Exception:
            db.session.rollback()
