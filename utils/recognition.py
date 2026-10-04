import numpy as np
from utils.database import db, Person, FaceEmbedding


def find_person(embedding, threshold=0.8, margin=0.05, top_k=10):
    """
    Finds the best matching person identity for a given face embedding.
    Uses pgvector's L2 distance operator.

    Margin check:
    Ensures the nearest match is separated by at least `margin` distance from
    the nearest match of any DIFFERENT person (preventing ambiguous multi-person matches).
    Multiple close embeddings for the SAME person reinforce the identity rather than penalizing it.

    Returns:
        tuple[str, float]: (person_name or "Unknown", best_distance)
    """
    if embedding is None or len(embedding) == 0:
        return "Unknown", 1.0

    emb_array = np.array(embedding, dtype=np.float32)
    norm = np.linalg.norm(emb_array)
    if norm > 0:
        emb_array = emb_array / norm
    else:
        return "Unknown", 1.0

    # Query top nearest neighbors among known faces
    closest_faces = (
        db.session.query(
            FaceEmbedding,
            FaceEmbedding.embedding.l2_distance(emb_array.tolist()).label("distance")
        )
        .filter(FaceEmbedding.person_id.isnot(None))
        .order_by("distance")
        .limit(top_k)
        .all()
    )

    if not closest_faces:
        return "Unknown", 1.0

    best_match, best_dist = closest_faces[0]
    best_dist = float(best_dist)

    # If best distance exceeds threshold, it's an unknown face
    if best_dist >= threshold:
        return "Unknown", best_dist

    # Find the closest match belonging to a DIFFERENT person
    other_person_dist = None
    for face, dist in closest_faces[1:]:
        if face.person_id != best_match.person_id:
            other_person_dist = float(dist)
            break

    # If there are no other persons in candidate results, margin is satisfied
    if other_person_dist is None:
        gap_ok = True
    else:
        gap_ok = (other_person_dist - best_dist) >= margin

    if gap_ok:
        person = db.session.get(Person, best_match.person_id)
        if person:
            return person.name, best_dist

    return "Unknown", best_dist

