from unittest import TestCase

from image_processing.severity import IPM_RECOMMENDATIONS, severity_level


class SeverityLevelTests(TestCase):
    def test_thresholds(self):
        leaf = 10000
        cases = [
            (0, 0), # S = 0%
            (1, 1), # S = 0.01%
            (499, 1), # 4.99%
            (500, 2), # đúng 5%
            (1499, 2),
            (1500, 3), # đúng 15%
            (3500, 3), # đúng 35% vẫn là cấp 3
            (3501, 4),
            (10000, 4),
        ]
        for lesion, level in cases:
            with self.subTest(lesion=lesion):
                self.assertEqual(severity_level(lesion, leaf), level)

    def test_leaf_area_must_be_positive(self):
        with self.assertRaises(ValueError):
            severity_level(0, 0)

    def test_recommendation_for_every_level(self):
        self.assertEqual(sorted(IPM_RECOMMENDATIONS), [0, 1, 2, 3, 4])
