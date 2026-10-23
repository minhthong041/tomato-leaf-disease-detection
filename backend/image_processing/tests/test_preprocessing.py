from unittest import TestCase

import cv2
import numpy as np

from image_processing import preprocessing, steps

TARGET_SHAPE = (preprocessing.TARGET_SIZE, preprocessing.TARGET_SIZE, 3)
# Sai lệch trung bình cho phép của kênh A, B sau equalize (do làm tròn uint8 khi đổi LAB <-> BGR)
AB_TOLERANCE = 1.0


def make_leaf(height=256, width=256):
    """Ảnh tổng hợp có kết cấu: lá elip xanh có đốm nâu trên nền sáng, cộng nhiễu cố định."""
    image = np.full((height, width, 3), (230, 230, 230), np.uint8)
    center = (width // 2, height // 2)
    cv2.ellipse(image, center, (width // 3, height // 4), 30, 0, 360, (40, 150, 50), -1)
    cv2.circle(image, center, min(height, width) // 12, (30, 70, 120), -1)
    noise = np.random.default_rng(0).integers(0, 20, image.shape, dtype=np.uint8)
    return cv2.add(image, noise)


def make_low_contrast(size=256):
    """Ảnh tương phản thấp: kênh sáng chỉ dao động trong khoảng hẹp 110–140."""
    gradient = np.linspace(110, 130, size, dtype=np.float64)
    gray = np.tile(gradient, (size, 1))
    gray += np.random.default_rng(0).integers(0, 10, gray.shape)
    gray = gray.astype(np.uint8)
    return cv2.merge((gray, gray, gray))


def lightness_std(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2LAB)[..., 0].std()


class ResizeTests(TestCase):
    def test_enlarge_small_square(self):
        result = preprocessing.resize(make_leaf(256, 256))
        self.assertEqual(result.shape, TARGET_SHAPE)
        self.assertEqual(result.dtype, np.uint8)

    def test_shrink_large_non_square(self):
        result = preprocessing.resize(make_leaf(800, 600))
        self.assertEqual(result.shape, TARGET_SHAPE)
        self.assertEqual(result.dtype, np.uint8)

    def test_mixed_dimensions(self):
        # Một chiều lớn hơn, một chiều nhỏ hơn TARGET_SIZE
        result = preprocessing.resize(make_leaf(300, 900))
        self.assertEqual(result.shape, TARGET_SHAPE)


class DenoiseEqualizeTests(TestCase):
    def test_denoise_keeps_shape_and_dtype(self):
        image = make_leaf(*TARGET_SHAPE[:2])
        result = preprocessing.denoise(image)
        self.assertEqual(result.shape, image.shape)
        self.assertEqual(result.dtype, np.uint8)

    def test_equalize_keeps_shape_and_dtype(self):
        image = make_leaf(*TARGET_SHAPE[:2])
        result = preprocessing.equalize(image)
        self.assertEqual(result.shape, image.shape)
        self.assertEqual(result.dtype, np.uint8)

    def test_equalize_increases_contrast_of_low_contrast_image(self):
        image = make_low_contrast()
        self.assertGreater(lightness_std(preprocessing.equalize(image)), lightness_std(image))

    def test_equalize_only_changes_lightness(self):
        # CLAHE chỉ chạy trên kênh L: kênh A, B chỉ lệch do làm tròn khi đổi LAB <-> BGR
        image = make_leaf(*TARGET_SHAPE[:2])
        before = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.int16)
        after = cv2.cvtColor(preprocessing.equalize(image), cv2.COLOR_BGR2LAB).astype(np.int16)
        self.assertFalse(np.array_equal(after[..., 0], before[..., 0]))
        self.assertLessEqual(np.abs(after[..., 1:] - before[..., 1:]).mean(), AB_TOLERANCE)

    def test_denoise_reduces_noise(self):
        image = make_low_contrast()
        self.assertLess(preprocessing.denoise(image).std(), image.std())


class PreprocessTests(TestCase):
    def test_returns_processed_image_and_three_steps(self):
        processed, step_images = preprocessing.preprocess(make_leaf())
        self.assertEqual(processed.shape, TARGET_SHAPE)
        self.assertEqual(processed.dtype, np.uint8)
        self.assertEqual(set(step_images), {steps.RESIZED, steps.DENOISED, steps.CLAHE})
        for name, image in step_images.items():
            self.assertEqual(image.shape, TARGET_SHAPE, name)
        np.testing.assert_array_equal(step_images[steps.CLAHE], processed)

    def test_input_not_modified(self):
        image = make_leaf()
        before = image.copy()
        preprocessing.preprocess(image)
        np.testing.assert_array_equal(image, before)
