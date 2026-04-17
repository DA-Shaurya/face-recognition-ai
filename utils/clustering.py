from sklearn.cluster import DBSCAN
import numpy as np

def cluster_faces(encodings):
    if len(encodings) == 0:
        return []

    X = np.array(encodings)

    # 🔥 NORMALIZE (MOST IMPORTANT FIX)
    X = X / np.linalg.norm(X, axis=1, keepdims=True)

    clustering = DBSCAN(
        eps=0.5,          # stricter
        min_samples=1,    
        metric='euclidean'
    ).fit(X)

    return clustering.labels_