from unittest import TestCase

import cv2
import numpy as np

from image_processing import errors, segmentation, steps


def synthetic_leaf():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.circle(image, (50, 50), 30, (0, 200, 0), -1)
    cv2.circle(image, (50, 50), 7, (0, 70, 120), -1)
    return image


def synthetic_leaf_with_lesions():
    image = np.full((160, 160, 3), 255, dtype=np.uint8)
    cv2.ellipse(image, (80, 80), (60, 50), 0, 0, 360, (0, 200, 0), -1)
    for center in ((45, 65), (115, 65), (80, 110)):
        cv2.circle(image, center, 7, (0, 80, 140), -1)
    return image


class SegmentationTests(TestCase):
    def test_segment_leaf_returns_empty_mask_for_white_image(self):
        image = np.full((100, 100, 3), 255, dtype=np.uint8)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(cv2.countNonZero(leaf_mask), 0)

    def test_segment_leaf_area_matches_theoretical_ellipse_area(self):
        image = np.full((180, 180, 3), 255, dtype=np.uint8)
        axis_a, axis_b = 70, 50
        cv2.ellipse(
            image, (90, 90), (axis_a, axis_b), 0, 0, 360, (0, 200, 0), -1,
        )

        leaf_mask, _ = segmentation.segment_leaf(image)
        actual_area = cv2.countNonZero(leaf_mask)
        theoretical_area = np.pi * axis_a * axis_b

        self.assertLessEqual(
            abs(actual_area - theoretical_area) / theoretical_area,
            0.02,
        )

    def test_segment_leaf_includes_interior_lesion(self):
        image = synthetic_leaf()

        leaf_mask, intermediate = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask.dtype, np.uint8)
        self.assertEqual(set(np.unique(leaf_mask)), {0, 255})
        self.assertGreater(cv2.countNonZero(leaf_mask), 2500)
        self.assertEqual(set(intermediate), {steps.SATURATION, steps.LEAF_MASK})
        self.assertEqual(leaf_mask[50, 50], 255)

    def test_segment_leaf_fills_necrosis_and_shadow_holes(self):
        image = np.full((140, 140, 3), 255, dtype=np.uint8)
        cv2.ellipse(image, (70, 70), (55, 45), 0, 0, 360, (0, 200, 0), -1)
        cv2.circle(image, (50, 60), 10, (0, 190, 255), -1)
        cv2.circle(image, (85, 60), 10, (0, 70, 120), -1)
        cv2.circle(image, (70, 85), 10, (35, 35, 35), -1)

        leaf_mask, intermediate = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[60, 50], 255)
        self.assertEqual(leaf_mask[60, 85], 255)
        self.assertEqual(leaf_mask[85, 70], 255)
        self.assertEqual(leaf_mask[10, 10], 0)
        self.assertEqual(set(np.unique(leaf_mask)), {0, 255})
        self.assertIs(intermediate[steps.LEAF_MASK], leaf_mask)

    def test_segment_leaf_fills_dark_leaf_but_excludes_adjacent_shadow(self):
        image = np.full((140, 140, 3), 255, dtype=np.uint8)
        cv2.ellipse(image, (55, 70), (28, 25), 0, 0, 360, (0, 200, 0), -1)
        cv2.ellipse(image, (65, 70), (5, 7), 0, 0, 360, (35, 35, 35), -1)
        cv2.ellipse(image, (89, 70), (8, 12), 0, 0, 360, (35, 35, 35), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[70, 65], 255)
        self.assertEqual(leaf_mask[70, 90], 0)
        self.assertEqual(leaf_mask[10, 10], 0)

    def test_segment_leaf_keeps_dark_green_lobe_fragment(self):
        image = np.full((140, 140, 3), 255, dtype=np.uint8)
        cv2.ellipse(image, (48, 70), (28, 32), 0, 0, 360, (0, 200, 0), -1)
        cv2.ellipse(image, (87, 70), (13, 20), 0, 0, 360, (0, 40, 0), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[70, 87], 255)
        self.assertEqual(leaf_mask[10, 10], 0)

    def test_segment_leaf_recovers_dark_necrosis_at_leaf_edge(self):
        image = np.full((140, 140, 3), 220, dtype=np.uint8)
        cv2.ellipse(image, (55, 70), (28, 25), 0, 0, 360, (0, 200, 0), -1)
        lesion_hsv = np.array([[[29, 195, 38]]], dtype=np.uint8)
        lesion_bgr = cv2.cvtColor(lesion_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.ellipse(
            image, (80, 70), (12, 10), 0, 0, 360,
            tuple(int(value) for value in lesion_bgr), -1,
        )

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[70, 85], 255)

    def test_segment_leaf_fills_deep_fold_inside_leaf(self):
        image = np.full((140, 140, 3), 220, dtype=np.uint8)
        cv2.ellipse(image, (70, 70), (45, 35), 0, 0, 360, (0, 200, 0), -1)
        fold_hsv = np.array([[[20, 39, 39]]], dtype=np.uint8)
        fold_bgr = cv2.cvtColor(fold_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.ellipse(
            image, (70, 70), (16, 10), 0, 0, 360,
            tuple(int(value) for value in fold_bgr), -1,
        )

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[70, 70], 255)

    def test_segment_leaf_keeps_low_chroma_petiole_connected(self):
        image = np.full((140, 140, 3), 220, dtype=np.uint8)
        cv2.ellipse(image, (70, 55), (25, 25), 0, 0, 360, (0, 200, 0), -1)
        petiole_hsv = np.array([[[150, 28, 110]]], dtype=np.uint8)
        petiole_bgr = cv2.cvtColor(petiole_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.line(
            image, (70, 78), (70, 115),
            tuple(int(value) for value in petiole_bgr), 3,
        )

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[100, 70], 255)

    def test_segment_leaf_excludes_shadow_over_textured_background(self):
        rng = np.random.default_rng(7)
        texture = rng.normal(0, 7, (140, 140, 1))
        image = np.clip(
            np.array([168, 164, 171], dtype=np.float32) + texture,
            0, 255,
        ).astype(np.uint8)
        shadow = np.clip(
            image.astype(np.float32) * 0.35 + np.array([-15, -3, 8]),
            0,
            255,
        ).astype(np.uint8)
        cv2.rectangle(
            image, (75, 25), (139, 115), (0, 0, 0), -1,
        )
        image[25:116, 75:] = shadow[25:116, 75:]
        cv2.ellipse(image, (50, 70), (25, 25), 0, 0, 360, (0, 200, 0), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[70, 50], 255)
        self.assertEqual(leaf_mask[70, 110], 0)

    def test_segment_leaf_excludes_warm_cast_shadow_touching_leaf(self):
        rng = np.random.default_rng(11)
        noise = rng.normal(0, 7, (140, 140, 1))
        image = np.clip(
            np.array([168, 164, 171], dtype=np.float32) + noise,
            0,
            255,
        ).astype(np.uint8)
        shadow_hsv = np.array([[[2, 78, 46]]], dtype=np.uint8)
        shadow_bgr = cv2.cvtColor(shadow_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.ellipse(
            image, (50, 70), (25, 25), 0, 0, 360, (0, 200, 0), -1,
        )
        cv2.ellipse(
            image, (89, 70), (19, 22), 0, 0, 360,
            tuple(int(value) for value in shadow_bgr), -1,
        )

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[70, 50], 255)
        self.assertEqual(leaf_mask[70, 100], 0)

    def test_segment_leaf_excludes_gray_shadow_near_leaf_edge(self):
        image = np.full((120, 120, 3), 255, dtype=np.uint8)
        cv2.circle(image, (60, 60), 25, (0, 200, 0), -1)
        cv2.circle(image, (60, 60), 31, (70, 70, 70), 3)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[60, 60], 255)
        self.assertEqual(leaf_mask[60, 90], 0)

    def test_leaf_mask_excludes_external_shadow(self):
        image = np.full((120, 120, 3), 255, dtype=np.uint8)
        cv2.circle(image, (60, 60), 25, (0, 200, 0), -1)
        cv2.rectangle(image, (90, 55), (94, 65), (70, 70, 70), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[60, 60], 255)
        self.assertTrue(np.all(leaf_mask[55:66, 90:95] == 0))

    def test_segment_leaf_includes_dark_brown_lesion_at_leaf_edge(self):
        image = np.full((120, 120, 3), 255, dtype=np.uint8)
        cv2.circle(image, (55, 60), 25, (0, 200, 0), -1)
        lesion_hsv = np.array([[[19, 70, 50]]], dtype=np.uint8)
        lesion_bgr = cv2.cvtColor(lesion_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.ellipse(
            image, (82, 60), (12, 15), 0, 0, 360,
            tuple(int(channel) for channel in lesion_bgr), -1,
        )

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[60, 55], 255)
        self.assertEqual(leaf_mask[60, 82], 255)

    def test_leaf_mask_preserves_lobe_gap(self):
        image = np.full((120, 120, 3), 255, dtype=np.uint8)
        cv2.circle(image, (35, 40), 20, (0, 200, 0), -1)
        cv2.circle(image, (86, 40), 20, (0, 200, 0), -1)
        cv2.rectangle(image, (20, 60), (100, 95), (0, 200, 0), -1)
        cv2.rectangle(image, (56, 5), (65, 59), (70, 70, 70), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[40, 35], 255)
        self.assertEqual(leaf_mask[40, 86], 255)
        self.assertTrue(np.all(leaf_mask[5:60, 56:66] == 0))

    def test_segment_leaf_rejects_low_saturation_tip_and_preserves_outer_notch(self):
        image = np.full((120, 120, 3), 220, dtype=np.uint8)
        leaf_points = np.array([
            [60, 8], [82, 34], [78, 44], [98, 48], [84, 62],
            [96, 82], [74, 76], [60, 105], [47, 76], [24, 82],
            [37, 62], [22, 48], [43, 44], [38, 34],
        ], dtype=np.int32)
        cv2.fillPoly(image, [leaf_points], (0, 180, 0))
        tip_hsv = np.array([[[10, 33, 132]]], dtype=np.uint8)
        tip_bgr = cv2.cvtColor(tip_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.circle(image, (60, 10), 2, tuple(int(v) for v in tip_bgr), -1)
        cv2.circle(image, (60, 55), 5, (35, 35, 35), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[10, 60], 0)
        self.assertEqual(leaf_mask[55, 60], 255)
        self.assertEqual(leaf_mask[55, 92], 0)
        self.assertEqual(leaf_mask[10, 10], 0)

    def test_segment_leaf_fills_low_saturation_fold_and_rejects_shadow(self):
        image = np.full((140, 140, 3), 220, dtype=np.uint8)
        cv2.ellipse(image, (65, 70), (28, 35), 0, 0, 360, (0, 180, 0), -1)
        tip_hsv = np.array([[[10, 33, 132]]], dtype=np.uint8)
        tip_bgr = cv2.cvtColor(tip_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.circle(image, (65, 36), 2, tuple(int(v) for v in tip_bgr), -1)
        shadow_hsv = np.array([[[10, 25, 80]]], dtype=np.uint8)
        shadow_bgr = cv2.cvtColor(shadow_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.ellipse(
            image, (101, 70), (9, 18), 0, 0, 360,
            tuple(int(v) for v in shadow_bgr), -1,
        )

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[36, 65], 255)
        self.assertEqual(leaf_mask[70, 101], 0)

    def test_segment_leaf_rejects_saturated_purple_background(self):
        image = np.full((120, 120, 3), (145, 110, 160), dtype=np.uint8)
        cv2.ellipse(image, (60, 60), (35, 25), 0, 0, 360, (0, 190, 0), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[60, 60], 255)
        self.assertEqual(leaf_mask[5, 5], 0)
        self.assertLess(cv2.countNonZero(leaf_mask), 3500)

    def test_segment_leaf_includes_brown_necrosis_at_leaf_edge(self):
        image = np.full((120, 120, 3), 255, dtype=np.uint8)
        cv2.ellipse(image, (50, 60), (35, 25), 0, 0, 360, (0, 190, 0), -1)
        cv2.ellipse(image, (81, 60), (10, 8), 0, 0, 360, (0, 70, 120), -1)

        leaf_mask, _ = segmentation.segment_leaf(image)

        self.assertEqual(leaf_mask[60, 88], 255)
        self.assertEqual(leaf_mask[5, 5], 0)

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

    def test_segment_lesions_detects_three_brown_spots(self):
        image = synthetic_leaf_with_lesions()
        leaf_mask, _ = segmentation.segment_leaf(image)

        lesion_mask, _ = segmentation.segment_lesions(image, leaf_mask)
        lesions = segmentation.measure_lesions(lesion_mask)

        self.assertEqual(len(lesions), 3)
        self.assertTrue(np.all((lesion_mask > 0) <= (leaf_mask > 0)))
        self.assertTrue(all(lesion['circularity'] <= 1.0 for lesion in lesions))

    def test_segment_lesions_ignores_spots_near_leaf_boundary(self):
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        cv2.circle(image, (50, 50), 30, (0, 200, 0), -1)
        cv2.circle(image, (50, 50), 8, (0, 70, 120), -1)
        cv2.circle(image, (50, 50), 33, (0, 70, 120), 4)
        leaf_mask = np.zeros((100, 100), dtype=np.uint8)
        cv2.circle(leaf_mask, (50, 50), 35, 255, -1)

        lesion_mask, _ = segmentation.segment_lesions(image, leaf_mask)

        self.assertEqual(lesion_mask[50, 18], 0)
        self.assertEqual(lesion_mask[50, 50], 255)

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

    def test_segment_lesions_ignores_dark_shadow_band_at_leaf_edge(self):
        # Bóng xám tối nằm trong leaf_mask, sát mép nhưng ngoài lề 5 pixel
        image = np.full((120, 120, 3), 200, dtype=np.uint8)
        cv2.circle(image, (60, 60), 45, (40, 160, 50), -1)
        cv2.circle(image, (60, 60), 36, (49, 61, 73), 6)
        leaf_mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.circle(leaf_mask, (60, 60), 45, 255, -1)

        lesion_mask, _ = segmentation.segment_lesions(image, leaf_mask)

        self.assertEqual(cv2.countNonZero(lesion_mask), 0)

    def test_segment_lesions_keeps_dark_necrosis_inside_leaf(self):
        # Cùng màu tối ít sắc với bóng ở test trên nhưng nằm giữa lá thì là mô hoại tử
        image = np.full((120, 120, 3), 200, dtype=np.uint8)
        cv2.circle(image, (60, 60), 45, (40, 160, 50), -1)
        cv2.circle(image, (60, 60), 10, (49, 61, 73), -1)
        leaf_mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.circle(leaf_mask, (60, 60), 45, 255, -1)

        lesion_mask, _ = segmentation.segment_lesions(image, leaf_mask)

        self.assertEqual(lesion_mask[60, 60], 255)

    def test_segment_lesions_keeps_colorless_necrosis_deep_inside_leaf(self):
        # Mô chết nâu đen có chroma dưới LESION_MIN_CHROMA, nằm sâu trong lá nên vẫn là vết bệnh
        image = np.full((120, 120, 3), 200, dtype=np.uint8)
        cv2.circle(image, (60, 60), 45, (40, 160, 50), -1)
        cv2.circle(image, (60, 60), 10, (35, 40, 50), -1)
        leaf_mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.circle(leaf_mask, (60, 60), 45, 255, -1)

        lesion_mask, _ = segmentation.segment_lesions(image, leaf_mask)

        self.assertEqual(lesion_mask[60, 60], 255)

    def test_segment_lesions_uses_fallback_reference_when_leaf_lacks_green(self):
        # Lá bệnh nặng gần như toàn nâu: trung vị cả lá sẽ là màu vết bệnh, nên phải dùng mốc dự phòng
        image = np.full((120, 120, 3), 230, dtype=np.uint8)
        cv2.circle(image, (60, 60), 45, (0, 80, 140), -1)
        cv2.circle(image, (60, 25), 4, (40, 160, 50), -1)
        leaf_mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.circle(leaf_mask, (60, 60), 45, 255, -1)

        lesion_mask, intermediate = segmentation.segment_lesions(image, leaf_mask)

        self.assertLess(
            cv2.countNonZero(intermediate[steps.HEALTHY_MASK]), segmentation.HEALTHY_REF_MIN_PX,
        )
        self.assertEqual(lesion_mask[60, 60], 255)
        self.assertGreater(cv2.countNonZero(lesion_mask), cv2.countNonZero(leaf_mask) // 2)

    def test_segment_lesions_reference_follows_leaf_color(self):
        # Lá xanh ngả vàng đồng đều không bị coi là bệnh; đốm nâu trên lá đó vẫn được tách
        image = np.full((120, 120, 3), 230, dtype=np.uint8)
        cv2.circle(image, (60, 60), 45, (30, 170, 120), -1)
        leaf_mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.circle(leaf_mask, (60, 60), 45, 255, -1)

        lesion_mask, intermediate = segmentation.segment_lesions(image, leaf_mask)
        self.assertEqual(cv2.countNonZero(lesion_mask), 0)
        self.assertEqual(intermediate[steps.HEALTHY_MASK][60, 60], 255)

        cv2.circle(image, (60, 60), 8, (0, 80, 140), -1)
        lesion_mask, _ = segmentation.segment_lesions(image, leaf_mask)
        self.assertEqual(lesion_mask[60, 60], 255)

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

    def test_measure_lesions_circle_has_high_circularity(self):
        mask = np.zeros((60, 60), dtype=np.uint8)
        cv2.circle(mask, (30, 30), 20, 255, -1)

        lesions = segmentation.measure_lesions(mask)

        self.assertEqual(len(lesions), 1)
        self.assertGreater(lesions[0]['circularity'], 0.85)

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
