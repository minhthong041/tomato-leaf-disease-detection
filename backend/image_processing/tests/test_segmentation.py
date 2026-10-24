from unittest import TestCase

import cv2
import numpy as np

from image_processing import errors, segmentation, steps


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

    def test_segment_leaf_finds_low_saturation_green_leaf(self):
        image = np.full((100, 100, 3), 245, dtype=np.uint8)
        cv2.circle(image, (50, 50), 30, (105, 125, 110), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)
        lesion_mask, _ = segmentation.segment_lesions(image, leaf_mask)

        self.assertEqual(leaf_mask[50, 50], 255)
        self.assertGreater(cv2.countNonZero(leaf_mask), 2500)
        self.assertEqual(cv2.countNonZero(lesion_mask), 0)

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

    def test_segment_lesions_ignores_neutral_gray_region(self):
        image = synthetic_leaf()
        cv2.rectangle(image, (42, 43), (47, 48), (145, 145, 145), -1)
        leaf_mask, _ = segmentation.segment_leaf(image)

        lesion_mask, intermediate = segmentation.segment_lesions(image, leaf_mask)

        self.assertEqual(intermediate[steps.HEALTHY_MASK][45, 45], 0)
        self.assertEqual(lesion_mask[45, 45], 0)

    def test_segment_lesions_ignores_dark_green_leaf_region(self):
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        cv2.circle(image, (50, 50), 30, (0, 200, 0), -1)
        cv2.rectangle(image, (45, 45), (54, 54), (0, 20, 0), -1)
        leaf_mask, _ = segmentation.segment_leaf(image)

        lesion_mask, _ = segmentation.segment_lesions(image, leaf_mask)

        self.assertEqual(leaf_mask[50, 50], 255)
        self.assertEqual(lesion_mask[50, 50], 0)

    def test_process_image_returns_requested_result_shape(self):
        image = synthetic_leaf()

        result = segmentation.process_image(image)

        self.assertEqual(
            set(result),
            {
                'mask_leaf', 'mask_healthy', 'mask_lesion', 'processed_image',
                'leaf_area_px', 'lesion_area_px', 'infected_ratio',
            },
        )
        self.assertEqual(result['leaf_area_px'], cv2.countNonZero(result['mask_leaf']))
        self.assertEqual(result['lesion_area_px'], cv2.countNonZero(result['mask_lesion']))
        self.assertAlmostEqual(
            result['infected_ratio'],
            result['lesion_area_px'] / result['leaf_area_px'],
        )
        self.assertEqual(result['processed_image'].shape, image.shape)

    def test_process_image_draws_on_original_resolution(self):
        image = synthetic_leaf()
        original = cv2.resize(image, (200, 200), interpolation=cv2.INTER_NEAREST)

        result = segmentation.process_image(image, original)

        self.assertEqual(result['processed_image'].shape, original.shape)
        self.assertFalse(np.array_equal(result['processed_image'], original))

    def test_process_image_raises_when_no_leaf_is_found(self):
        image = np.full((40, 40, 3), 128, dtype=np.uint8)

        with self.assertRaisesRegex(errors.PipelineError, 'Không tìm thấy lá'):
            segmentation.process_image(image)

    def test_measure_lesions_empty_mask(self):
        empty = np.zeros((20, 20), dtype=np.uint8)

        self.assertEqual(segmentation.measure_lesions(empty), [])

    def test_measure_lesions_uses_exact_pixel_area(self):
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[2:5, 3:6] = 255
        mask[10, 10] = 255

        lesions = segmentation.measure_lesions(mask)

        self.assertEqual(sorted(lesion['area'] for lesion in lesions), [1, 9])
        self.assertEqual(sum(lesion['area'] for lesion in lesions), cv2.countNonZero(mask))

    def test_draw_lesions_rejects_mask_with_different_resolution(self):
        image = np.zeros((20, 20, 3), dtype=np.uint8)
        mask = np.zeros((10, 10), dtype=np.uint8)

        with self.assertRaisesRegex(ValueError, 'shape'):
            segmentation.draw_lesions(image, mask)

    def test_invalid_leaf_mask_is_rejected(self):
        image = synthetic_leaf()
        invalid_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        invalid_mask[0, 0] = 1

        with self.assertRaisesRegex(ValueError, '0 và 255'):
            segmentation.segment_lesions(image, invalid_mask)
