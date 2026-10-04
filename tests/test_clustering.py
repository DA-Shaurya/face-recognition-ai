import unittest
import numpy as np
from utils.clustering import cluster_faces


class TestClustering(unittest.TestCase):
    def test_empty_encodings(self):
        result = cluster_faces([])
        self.assertEqual(len(result), 0)

    def test_none_encodings(self):
        result = cluster_faces(None)
        self.assertEqual(len(result), 0)

    def test_single_encoding(self):
        emb = np.random.randn(512).astype(np.float32)
        labels = cluster_faces([emb])
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0], 0)

    def test_identical_encodings_grouped(self):
        base = np.random.randn(512).astype(np.float32)
        base = base / np.linalg.norm(base)
        # 3 identical or almost identical vectors
        encodings = [base, base + 1e-5, base - 1e-5]
        labels = cluster_faces(encodings, eps=0.5, min_samples=1)
        self.assertEqual(len(labels), 3)
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(labels[1], labels[2])

    def test_distinct_encodings_separated(self):
        # Orthogonal vectors in high dimensions
        v1 = np.zeros(512, dtype=np.float32)
        v1[0] = 1.0
        v2 = np.zeros(512, dtype=np.float32)
        v2[1] = 1.0

        labels = cluster_faces([v1, v2], eps=0.5, min_samples=1)
        self.assertEqual(len(labels), 2)
        self.assertNotEqual(labels[0], labels[1])

    def test_zero_vector_handled_safely(self):
        zero_emb = np.zeros(512, dtype=np.float32)
        labels = cluster_faces([zero_emb])
        self.assertEqual(len(labels), 1)


if __name__ == "__main__":
    unittest.main()
