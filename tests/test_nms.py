import unittest
from utils.deepface_utils import _iou, _nms


class TestNMS(unittest.TestCase):
    def test_iou_identical_boxes(self):
        box1 = {"x": 10, "y": 10, "w": 50, "h": 50}
        box2 = {"x": 10, "y": 10, "w": 50, "h": 50}
        self.assertAlmostEqual(_iou(box1, box2), 1.0)

    def test_iou_disjoint_boxes(self):
        box1 = {"x": 0, "y": 0, "w": 10, "h": 10}
        box2 = {"x": 100, "y": 100, "w": 20, "h": 20}
        self.assertAlmostEqual(_iou(box1, box2), 0.0)

    def test_iou_partial_overlap(self):
        box1 = {"x": 0, "y": 0, "w": 10, "h": 10}   # Area 100
        box2 = {"x": 5, "y": 0, "w": 10, "h": 10}   # Area 100, Inter: 5*10=50
        # Union = 100 + 100 - 50 = 150. IoU = 50/150 = 1/3
        self.assertAlmostEqual(_iou(box1, box2), 1.0 / 3.0)

    def test_nms_suppresses_redundant_boxes(self):
        faces = [
            {"box": {"x": 10, "y": 10, "w": 40, "h": 40}, "embedding": [0.1]},  # smaller box
            {"box": {"x": 10, "y": 10, "w": 50, "h": 50}, "embedding": [0.2]},  # larger box
        ]
        kept = _nms(faces, iou_threshold=0.25)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["box"]["w"], 50)

    def test_nms_keeps_separate_faces(self):
        faces = [
            {"box": {"x": 0, "y": 0, "w": 30, "h": 30}, "embedding": [0.1]},
            {"box": {"x": 200, "y": 200, "w": 30, "h": 30}, "embedding": [0.2]},
        ]
        kept = _nms(faces, iou_threshold=0.25)
        self.assertEqual(len(kept), 2)

    def test_nms_empty(self):
        self.assertEqual(_nms([]), [])


if __name__ == "__main__":
    unittest.main()
