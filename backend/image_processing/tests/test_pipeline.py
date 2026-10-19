import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest import TestCase, mock

import cv2
import numpy as np

from image_processing import classifier, pipeline, preprocessing, segmentation, steps

SIZE = 64


def fake_preprocess(image):
    return image, {steps.RESIZED: image, steps.DENOISED: image, steps.CLAHE: image}


def square_mask(start, end):
    mask = np.zeros((SIZE, SIZE), np.uint8)
    mask[start:end, start:end] = 255
    return mask


class FakeStages:
    """Thay các giai đoạn chưa cài đặt bằng kết quả cố định để kiểm tra phần ghép nối."""

    def __init__(self, leaf_mask, lesion_mask, lesion_step_names=None):
        self.leaf_mask = leaf_mask
        self.lesion_mask = lesion_mask
        self.lesion_step_names = lesion_step_names or (
            steps.ROI, steps.HEALTHY_MASK, steps.LESION_MASK_RAW, steps.LESION_MASK,
        )

    def segment_leaf(self, image):
        return self.leaf_mask, {steps.SATURATION: image[:, :, 1], steps.LEAF_MASK: self.leaf_mask}

    def segment_lesions(self, image, leaf_mask):
        return self.lesion_mask, {name: self.lesion_mask for name in self.lesion_step_names}

    def measure_lesions(self, lesion_mask):
        return [{'area': 1} for _ in range(1 if lesion_mask.any() else 0)]

    def patches(self):
        return [
            mock.patch.object(preprocessing, 'preprocess', fake_preprocess),
            mock.patch.object(segmentation, 'segment_leaf', self.segment_leaf),
            mock.patch.object(segmentation, 'segment_lesions', self.segment_lesions),
            mock.patch.object(segmentation, 'measure_lesions', self.measure_lesions),
            mock.patch.object(segmentation, 'draw_lesions', lambda image, mask: image.copy()),
            mock.patch.object(classifier, 'extract_features', lambda image, mask: np.zeros(3)),
            mock.patch.object(classifier, 'predict', lambda features: ('Tomato___Early_blight', 0.87654)),
        ]

    def run(self):
        image = np.full((SIZE, SIZE, 3), 120, np.uint8)
        with ExitStack() as stack:
            for patch in self.patches():
                stack.enter_context(patch)
            return pipeline.run(image)


class PipelineContractTests(TestCase):
    def test_diseased_leaf(self):
        # Lá 40x40 = 1600 px, vết bệnh 10x10 = 100 px -> S = 6.25% -> cấp 2
        result = FakeStages(square_mask(10, 50), square_mask(20, 30)).run()
        self.assertEqual(result.leaf_area_px, 1600)
        self.assertEqual(result.lesion_area_px, 100)
        self.assertEqual(result.infected_ratio, 0.0625)
        self.assertEqual(result.severity_level, 2)
        self.assertEqual(result.lesion_count, 1)
        self.assertEqual(result.disease_code, 'Tomato___Early_blight')
        self.assertEqual(result.disease_confidence, 0.8765)
        self.assertEqual(tuple(result.steps), steps.ORDER)
        self.assertIn('ngưỡng hành động', result.recommendation)

    def test_healthy_leaf(self):
        empty = np.zeros((SIZE, SIZE), np.uint8)
        result = FakeStages(square_mask(10, 50), empty).run()
        self.assertEqual((result.severity_level, result.lesion_area_px, result.lesion_count), (0, 0, 0))

    def test_no_leaf_found(self):
        empty = np.zeros((SIZE, SIZE), np.uint8)
        with self.assertRaises(pipeline.PipelineError):
            FakeStages(empty, empty).run()

    def test_lesion_outside_leaf(self):
        with self.assertRaisesRegex(ValueError, 'ngoài leaf_mask'):
            FakeStages(square_mask(10, 30), square_mask(25, 40)).run()

    def test_mask_must_be_binary(self):
        leaf = square_mask(10, 50)
        leaf[0, 0] = 1
        with self.assertRaisesRegex(ValueError, '0 và 255'):
            FakeStages(leaf, square_mask(20, 30)).run()

    def test_missing_step_image(self):
        stages = FakeStages(square_mask(10, 50), square_mask(20, 30), lesion_step_names=(steps.LESION_MASK,))
        with self.assertRaisesRegex(ValueError, 'Ảnh trung gian'):
            stages.run()


class LoadImageTests(TestCase):
    def test_path_with_vietnamese_name(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ảnh lá cà chua.png'
            _, buffer = cv2.imencode('.png', np.full((8, 8, 3), 200, np.uint8))
            buffer.tofile(str(path))
            self.assertEqual(pipeline.load_image(path).shape, (8, 8, 3))

    def test_not_an_image(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'khong-phai-anh.jpg'
            path.write_text('abc')
            with self.assertRaises(pipeline.PipelineError):
                pipeline.load_image(path)
