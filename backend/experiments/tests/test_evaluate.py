import tempfile
from pathlib import Path
from unittest import TestCase, mock

import cv2
import numpy as np

from experiments import evaluate
from image_processing import preprocessing

SIZE = 64


def rect_mask(top, left, bottom, right, size=SIZE):
    mask = np.zeros((size, size), np.uint8)
    mask[top:bottom, left:right] = 255
    return mask


EMPTY = np.zeros((SIZE, SIZE), np.uint8)


class IouDiceTests(TestCase):
    def test_identical_masks(self):
        mask = rect_mask(10, 10, 40, 40)
        self.assertEqual(evaluate.iou(mask, mask), 1.0)
        self.assertEqual(evaluate.dice(mask, mask), 1.0)

    def test_half_overlap(self):
        # Hai hình chữ nhật 20x10 trùng nhau một nửa: giao 100, hợp 300, tổng 400
        pred = rect_mask(0, 0, 10, 20)
        truth = rect_mask(0, 10, 10, 30)
        self.assertAlmostEqual(evaluate.iou(pred, truth), 100 / 300)
        self.assertAlmostEqual(evaluate.dice(pred, truth), 2 * 100 / 400)

    def test_both_empty(self):
        self.assertEqual(evaluate.iou(EMPTY, EMPTY), 1.0)
        self.assertEqual(evaluate.dice(EMPTY, EMPTY), 1.0)

    def test_one_empty(self):
        mask = rect_mask(10, 10, 20, 20)
        self.assertEqual(evaluate.iou(mask, EMPTY), 0.0)
        self.assertEqual(evaluate.dice(EMPTY, mask), 0.0)

    def test_disjoint(self):
        self.assertEqual(evaluate.iou(rect_mask(0, 0, 10, 10), rect_mask(20, 20, 30, 30)), 0.0)


class EvaluateImageTests(TestCase):
    def test_metrics_and_levels(self):
        leaf = rect_mask(0, 0, 40, 50) # 2000 điểm
        lesion_true = rect_mask(0, 0, 10, 20) # 200 điểm = 10% -> cấp 2
        lesion_pred = rect_mask(0, 0, 10, 40) # 400 điểm = 20% -> cấp 3
        row = evaluate.evaluate_image(leaf, lesion_true, leaf, lesion_pred)
        self.assertEqual(row['iou_la'], 1.0)
        self.assertAlmostEqual(row['iou_vet_benh'], 0.5)
        self.assertAlmostEqual(row['s_that'], 10.0)
        self.assertAlmostEqual(row['s_du_doan'], 20.0)
        self.assertAlmostEqual(row['sai_so_s'], 10.0)
        self.assertEqual((row['cap_that'], row['cap_du_doan']), (2, 3))
        self.assertFalse(row['sat_nguong'])

    def test_empty_lesion_truth_skips_lesion_overlap(self):
        leaf = rect_mask(0, 0, 40, 50)
        row = evaluate.evaluate_image(leaf, EMPTY, leaf, rect_mask(0, 0, 2, 2))
        self.assertIsNone(row['iou_vet_benh'])
        self.assertIsNone(row['dice_vet_benh'])
        self.assertEqual(row['cap_that'], 0)
        self.assertGreater(row['s_du_doan'], 0)

    def test_no_predicted_leaf(self):
        leaf = rect_mask(0, 0, 40, 50)
        row = evaluate.evaluate_image(leaf, EMPTY, EMPTY, EMPTY)
        self.assertEqual(row['iou_la'], 0.0)
        self.assertIsNone(row['cap_du_doan'])

    def test_near_threshold(self):
        self.assertTrue(evaluate.is_near_threshold(14.5))
        self.assertTrue(evaluate.is_near_threshold(35.9))
        self.assertFalse(evaluate.is_near_threshold(10.0))
        self.assertFalse(evaluate.is_near_threshold(0.0))


def write_png(path, image):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imencode('.png', image)[1].tofile(str(path))


class GroundTruthTests(TestCase):
    """Bộ dữ liệu tạm có cấu trúc giống dataset/: splits/, masks/leaf/, masks/lesion/."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        image = np.full((32, 32, 3), 200, np.uint8)
        write_png(self.root / 'plantvillage' / 'Tomato___Early_blight' / 'la 1.png', image)
        (self.root / 'splits').mkdir()
        self.list_file = self.root / 'splits' / 'ground_truth.txt'
        self.list_file.write_text('plantvillage/Tomato___Early_blight/la 1.png\n', encoding='utf-8')
        self.leaf = rect_mask(4, 4, 28, 28, size=32)
        self.lesion = rect_mask(8, 8, 12, 12, size=32)

    def tearDown(self):
        self.tmp.cleanup()

    def write_masks(self, leaf, lesion):
        write_png(self.root / 'masks' / 'leaf' / 'la 1.png', leaf)
        write_png(self.root / 'masks' / 'lesion' / 'la 1.png', lesion)

    def test_masks_scaled_to_preprocessed_size(self):
        self.write_masks(self.leaf, self.lesion)
        [item] = evaluate.load_ground_truth(self.list_file, self.root / 'masks')
        size = preprocessing.TARGET_SIZE
        self.assertEqual(item.disease, 'Tomato___Early_blight')
        self.assertEqual(item.leaf_mask.shape, (size, size))
        self.assertTrue(np.isin(item.leaf_mask, (0, 255)).all())
        # Phóng bằng INTER_NEAREST giữ nguyên tỷ lệ diện tích
        scale = (size // 32) ** 2
        self.assertEqual(cv2.countNonZero(item.leaf_mask), cv2.countNonZero(self.leaf) * scale)
        self.assertEqual(cv2.countNonZero(item.lesion_mask), cv2.countNonZero(self.lesion) * scale)

    def test_missing_mask(self):
        write_png(self.root / 'masks' / 'leaf' / 'la 1.png', self.leaf)
        with self.assertRaises(FileNotFoundError):
            evaluate.load_ground_truth(self.list_file, self.root / 'masks')

    def test_lesion_outside_leaf(self):
        self.write_masks(self.leaf, rect_mask(0, 0, 3, 3, size=32))
        with self.assertRaises(ValueError):
            evaluate.load_ground_truth(self.list_file, self.root / 'masks')

    def test_unimplemented_stage_is_skipped(self):
        self.write_masks(self.leaf, self.lesion)
        items = evaluate.load_ground_truth(self.list_file, self.root / 'masks')
        with mock.patch.object(evaluate, 'predict_masks', side_effect=NotImplementedError('segment_leaf')), \
                mock.patch('sys.stderr'):
            [row] = evaluate.evaluate_all(items)
        self.assertIn('chưa cài đặt', row['loi'])
        self.assertNotIn('iou_la', row)
        self.assertEqual(evaluate.summarize([row])['so_anh'], 0)
