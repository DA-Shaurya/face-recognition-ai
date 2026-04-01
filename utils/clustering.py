from sklearn.cluster import DBSCAN

def cluster_faces(encodings):
    if len(encodings) == 0:
        return []

    model = DBSCAN(metric='euclidean', eps=10, min_samples=1)
    labels = model.fit_predict(encodings)

    return labels