from unittest import TestCase

import cv2
import numpy as np

from image_processing import classifier

SIZE = 128
CENTER = (SIZE // 2, SIZE // 2)
RADIUS = 45
LEAF_GREEN = (40, 160, 40)  # BGR
LESION_BROWN = (30, 70, 120)  # BGR


def make_leaf(background=(255, 255, 255)):
    """Ảnh tổng hợp: lá tròn xanh có một đốm nâu và nhiễu cố định, trên nền đơn sắc."""
    image = np.full((SIZE, SIZE, 3), background, np.uint8)
    cv2.circle(image, CENTER, RADIUS, LEAF_GREEN, -1)
    cv2.circle(image, (CENTER[0] - 12, CENTER[1] - 8), 10, LESION_BROWN, -1)

    mask = np.zeros((SIZE, SIZE), np.uint8)
    cv2.circle(mask, CENTER, RADIUS, 255, -1)

    # Nhiễu cố định chỉ trên lá để có kết cấu cho GLCM; nền giữ nguyên màu
    noise = np.random.default_rng(0).integers(0, 25, image.shape, dtype=np.uint8)
    leaf = mask == 255
    image[leaf] = cv2.add(image, noise)[leaf]
    return image, mask


class ExtractFeaturesTests(TestCase):
    def test_vector_length_and_dtype(self):
        image, mask = make_leaf()
        features = classifier.extract_features(image, mask)
        self.assertEqual(features.shape, (len(classifier.FEATURE_NAMES),))
        self.assertEqual(features.dtype, np.float64)
        self.assertTrue(np.isfinite(features).all())

    def test_feature_names_unique(self):
        self.assertEqual(
            len(set(classifier.FEATURE_NAMES)), len(classifier.FEATURE_NAMES)
        )

    def test_deterministic(self):
        image, mask = make_leaf()
        first = classifier.extract_features(image, mask)
        second = classifier.extract_features(image.copy(), mask.copy())
        np.testing.assert_array_equal(first, second)

    def test_background_does_not_matter(self):
        white, mask = make_leaf(background=(255, 255, 255))
        black, _ = make_leaf(background=(0, 0, 0))
        blue, _ = make_leaf(background=(200, 50, 20))
        expected = classifier.extract_features(white, mask)
        np.testing.assert_allclose(classifier.extract_features(black, mask), expected)
        np.testing.assert_allclose(classifier.extract_features(blue, mask), expected)

    def test_input_not_modified(self):
        image, mask = make_leaf()
        image_before, mask_before = image.copy(), mask.copy()
        classifier.extract_features(image, mask)
        np.testing.assert_array_equal(image, image_before)
        np.testing.assert_array_equal(mask, mask_before)

    def test_uniform_leaf_has_no_nan(self):
        image = np.full((SIZE, SIZE, 3), LEAF_GREEN, np.uint8)
        mask = np.full((SIZE, SIZE), 255, np.uint8)
        features = classifier.extract_features(image, mask)
        self.assertTrue(np.isfinite(features).all())

    def test_empty_mask_raises(self):
        image, _ = make_leaf()
        with self.assertRaises(ValueError):
            classifier.extract_features(image, np.zeros((SIZE, SIZE), np.uint8))

    def test_wrong_mask_shape_raises(self):
        image, _ = make_leaf()
        with self.assertRaises(ValueError):
            classifier.extract_features(
                image, np.full((SIZE // 2, SIZE // 2), 255, np.uint8)
            )
