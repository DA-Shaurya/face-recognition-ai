import unittest
from unittest.mock import patch, MagicMock

try:
    import redis
    import flask_sqlalchemy
    import flask_session
    import pillow_heif
    from app import app
    HAS_APP = True
except Exception:
    HAS_APP = False



@unittest.skipUnless(HAS_APP, "Flask full microservice dependencies (redis, flask_sqlalchemy) required for API integration test")
class TestApi(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_404_handler(self):
        res = self.client.get("/non_existent_route")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertIn("error", data)

    def test_settings_get(self):
        res = self.client.get("/settings")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("confidence_threshold", data)
        self.assertIn("margin_threshold", data)

    def test_settings_post_update(self):
        res = self.client.post("/settings", json={
            "confidence_threshold": 0.75,
            "margin_threshold": 0.08
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["confidence_threshold"], 0.75)
        self.assertEqual(data["margin_threshold"], 0.08)

    def test_add_person_validation(self):
        # Missing both fields
        res = self.client.post("/add_person", json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())

        # Missing image
        res = self.client.post("/add_person", json={"name": "Alice"})
        self.assertEqual(res.status_code, 400)

    def test_delete_person_validation(self):
        # Missing name
        res = self.client.post("/delete_person", json={})
        self.assertEqual(res.status_code, 400)

    def test_rename_person_validation(self):
        # Missing new_name
        res = self.client.post("/rename_person", json={"old_name": "Alice"})
        self.assertEqual(res.status_code, 400)

    def test_delete_image_validation(self):
        res = self.client.post("/delete_image", json={})
        self.assertEqual(res.status_code, 400)

    @patch("app.redis_client")
    def test_health_check(self, mock_redis):
        mock_redis.ping.return_value = True
        res = self.client.get("/health")
        self.assertIn(res.status_code, [200, 503])
        data = res.get_json()
        self.assertIn("redis", data)
        self.assertIn("db", data)


if __name__ == "__main__":
    unittest.main()
