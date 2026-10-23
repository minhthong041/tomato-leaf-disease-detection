from unittest import TestCase

import cv2
import numpy as np

from image_processing import segmentation, steps


def synthetic_leaf():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.circle(image, (50, 50), 30, (0, 200, 0), -1)
    cv2.circle(image, (50, 50), 7, (0, 70, 120), -1)
    return image


class SegmentationTests(TestCase):
    def test_segment_leaf_includes_interior_lesion(self):
        image = synthetic_leaf()

        leaf_mask, intermediate = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask.dtype, np.uint8)
        self.assertEqual(set(np.unique(leaf_mask)), {0, 255})
        self.assertGreater(cv2.countNonZero(leaf_mask), 2500)
        self.assertEqual(set(intermediate), {steps.SATURATION, steps.LEAF_MASK})
        self.assertEqual(leaf_mask[50, 50], 255)

    def test_segment_lesions_stays_inside_leaf(self):
        image = synthetic_leaf()
        leaf_mask, _ = segmentation.segment_leaf(image)

        lesion_mask, intermediate = segmentation.segment_lesions(image, leaf_mask)

        self.assertEqual(set(np.unique(lesion_mask)), {0, 255})
        self.assertTrue(np.all((lesion_mask > 0) <= (leaf_mask > 0)))
        self.assertGreater(cv2.countNonZero(lesion_mask), 0)
        self.assertEqual(
            set(intermediate),
            {steps.ROI, steps.HEALTHY_MASK, steps.LESION_MASK_RAW, steps.LESION_MASK},
        )
        self.assertEqual(intermediate[steps.HEALTHY_MASK][50, 50], 0)

    def test_process_image_returns_requested_result_shape(self):
        image = synthetic_leaf()

        result = segmentation.process_image(image)

        self.assertEqual(
            set(result),
            {
                'mask_leaf', 'mask_healthy', 'mask_lesion', 'contour_img',
                'area_leaf', 'area_lesion', 'severity_ratio',
            },
        )
        self.assertEqual(result['area_leaf'], cv2.countNonZero(result['mask_leaf']))
        self.assertEqual(result['area_lesion'], cv2.countNonZero(result['mask_lesion']))
        self.assertAlmostEqual(
            result['severity_ratio'],
            result['area_lesion'] / result['area_leaf'] * 100,
        )
        self.assertEqual(result['contour_img'].shape, image.shape)

    def test_process_image_draws_on_original_resolution(self):
        image = synthetic_leaf()
        original = cv2.resize(image, (200, 200), interpolation=cv2.INTER_NEAREST)

        result = segmentation.process_image(image, original)

        self.assertEqual(result['contour_img'].shape, original.shape)
        self.assertFalse(np.array_equal(result['contour_img'], original))

    def test_measure_lesions_empty_mask(self):
        empty = np.zeros((20, 20), dtype=np.uint8)

        self.assertEqual(segmentation.measure_lesions(empty), [])

    def test_invalid_leaf_mask_is_rejected(self):
        image = synthetic_leaf()
        invalid_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        invalid_mask[0, 0] = 1

        with self.assertRaisesRegex(ValueError, '0 và 255'):
            segmentation.segment_lesions(image, invalid_mask)
