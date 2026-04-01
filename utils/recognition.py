import numpy as np
from utils.embedding_store import load_embeddings

def load_known_faces():
    return load_embeddings()


def find_person(embedding, known_faces):
    import numpy as np

    # 🔥 normalize input embedding ONCE
    embedding = np.array(embedding)
    embedding = embedding / np.linalg.norm(embedding)

    if not known_faces:
        return "Unknown", 1.0

    distances = []

    for name, embeddings_list in known_faces.items():
        for known_emb in embeddings_list:

            # 🔥 normalize stored embedding
            known_emb = np.array(known_emb)
            known_emb = known_emb / np.linalg.norm(known_emb)

            # 🔥 compute distance
            distance = np.linalg.norm(embedding - known_emb)

            print(f"{name} distance = {distance}")

            distances.append((name, distance))

    if not distances:
        return "Unknown", 1.0

    # sort by closest
    distances.sort(key=lambda x: x[1])

    best_match, best_distance = distances[0]

    # second best (for confidence gap)
    second_best = distances[1][1] if len(distances) > 1 else 1.0

    print(f"Best: {best_match}, distance = {best_distance}")

    # 🔥 improved decision logic
    if best_distance < 0.8 and (second_best - best_distance) > 0.05:
        return best_match, best_distance
    else:
        return "Unknown", best_distance