import numpy as np
from utils.database import db, Person, FaceEmbedding

def find_person(embedding, threshold=0.8, margin=0.05):
    """
    Returns (name, distance).
    Uses pgvector's L2 distance operator.
    """
    emb_array = np.array(embedding, dtype=np.float32)
    norm = np.linalg.norm(emb_array)
    if norm > 0:
        emb_array = emb_array / norm

    # Query for nearest neighbors
    # We only want known faces
    closest_faces = db.session.query(FaceEmbedding, FaceEmbedding.embedding.l2_distance(emb_array.tolist()).label('distance')) \
        .filter(FaceEmbedding.person_id.isnot(None)) \
        .order_by('distance') \
        .limit(2) \
        .all()

    if not closest_faces:
        return "Unknown", 1.0

    best_match, best_dist = closest_faces[0]
    second_dist = closest_faces[1].distance if len(closest_faces) > 1 else 1.0

    gap_ok = (second_dist - best_dist) > margin
    threshold_ok = best_dist < threshold

    if threshold_ok and gap_ok:
        person = db.session.get(Person, best_match.person_id)
        if person:
            return person.name, float(best_dist)

    return "Unknown", float(best_dist)
