import sys
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

# Stub database module if flask_sqlalchemy is not installed in local environment
if "utils.database" not in sys.modules:
    try:
        from utils.database import db, Person, FaceEmbedding
    except ImportError:
        mock_db_mod = MagicMock()
        mock_db_mod.db = MagicMock()
        mock_db_mod.Person = MagicMock()
        mock_db_mod.FaceEmbedding = MagicMock()
        sys.modules["utils.database"] = mock_db_mod

from utils.recognition import find_person, db


class TestRecognition(unittest.TestCase):
    def test_empty_or_none_embedding(self):
        name, dist = find_person([])
        self.assertEqual(name, "Unknown")
        self.assertEqual(dist, 1.0)

        name, dist = find_person(None)
        self.assertEqual(name, "Unknown")
        self.assertEqual(dist, 1.0)

    @patch("utils.recognition.db")
    def test_no_known_faces_in_db(self, mock_db):
        query_mock = MagicMock()
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.session.query.return_value = query_mock

        dummy_emb = [0.1] * 512
        name, dist = find_person(dummy_emb)
        self.assertEqual(name, "Unknown")
        self.assertEqual(dist, 1.0)

    @patch("utils.recognition.db")
    def test_confident_single_match(self, mock_db):
        mock_face = MagicMock()
        mock_face.person_id = 1

        mock_person = MagicMock()
        mock_person.name = "alice"
        mock_db.session.get.return_value = mock_person

        query_mock = MagicMock()
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            (mock_face, 0.30)
        ]
        mock_db.session.query.return_value = query_mock

        dummy_emb = [0.1] * 512
        name, dist = find_person(dummy_emb, threshold=0.8, margin=0.05)
        self.assertEqual(name, "alice")
        self.assertAlmostEqual(dist, 0.30)

    @patch("utils.recognition.db")
    def test_same_person_multiple_matches_not_penalized(self, mock_db):
        """
        Regression test: When 1st and 2nd closest matches belong to the SAME person,
        the ambiguity margin should not penalize the match.
        """
        face1 = MagicMock(person_id=1)
        face2 = MagicMock(person_id=1)  # same person

        mock_person = MagicMock()
        mock_person.name = "alice"
        mock_db.session.get.return_value = mock_person

        query_mock = MagicMock()
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            (face1, 0.20),
            (face2, 0.21),  # difference is only 0.01 < margin(0.05)
        ]
        mock_db.session.query.return_value = query_mock

        dummy_emb = [0.1] * 512
        name, dist = find_person(dummy_emb, threshold=0.8, margin=0.05)
        self.assertEqual(name, "alice")
        self.assertAlmostEqual(dist, 0.20)

    @patch("utils.recognition.db")
    def test_ambiguous_different_person_rejected(self, mock_db):
        """
        When closest match is person 1 (dist 0.40) and 2nd match is person 2 (dist 0.42),
        margin difference (0.02) < margin (0.05) -> returns Unknown.
        """
        face1 = MagicMock(person_id=1)
        face2 = MagicMock(person_id=2)  # different person

        query_mock = MagicMock()
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            (face1, 0.40),
            (face2, 0.42),
        ]
        mock_db.session.query.return_value = query_mock

        dummy_emb = [0.1] * 512
        name, dist = find_person(dummy_emb, threshold=0.8, margin=0.05)
        self.assertEqual(name, "Unknown")
        self.assertAlmostEqual(dist, 0.40)

    @patch("utils.recognition.db")
    def test_exceeds_distance_threshold(self, mock_db):
        face1 = MagicMock(person_id=1)

        query_mock = MagicMock()
        query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            (face1, 0.95),  # exceeds 0.8
        ]
        mock_db.session.query.return_value = query_mock

        dummy_emb = [0.1] * 512
        name, dist = find_person(dummy_emb, threshold=0.8, margin=0.05)
        self.assertEqual(name, "Unknown")
        self.assertAlmostEqual(dist, 0.95)


if __name__ == "__main__":
    unittest.main()
