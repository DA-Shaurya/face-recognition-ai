import os
import numpy as np
from sklearn.cluster import DBSCAN


def cluster_faces(encodings, eps=None, min_samples=None):
    """
    Clusters face embeddings using DBSCAN with L2 distance on unit-normalized vectors.

    Args:
        encodings: list or np.ndarray of shape (N, D) containing face embedding vectors.
        eps: DBSCAN maximum distance between two samples for one to be considered
             as in the neighborhood of the other. Defaults to DBSCAN_EPS env var or 0.5.
        min_samples: The number of samples in a neighborhood for a point to be
                     considered as a core point. Defaults to DBSCAN_MIN_SAMPLES env var or 1.

    Returns:
        np.ndarray: Cluster labels for each point. Noisy samples are given the label -1.
    """
    if encodings is None or len(encodings) == 0:
        return np.array([], dtype=int)

    X = np.asarray(encodings, dtype=np.float32)

    # 1D single vector safeguard
    if X.ndim == 1:
        return np.array([0], dtype=int)

    # Unit-normalize vectors with safe zero division
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X = X / norms

    if eps is None:
        eps = float(os.getenv("DBSCAN_EPS", "0.5"))
    if min_samples is None:
        min_samples = int(os.getenv("DBSCAN_MIN_SAMPLES", "1"))

    clustering = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric="euclidean"
    ).fit(X)

    return clustering.labels_