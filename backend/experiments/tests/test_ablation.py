import contextlib
import csv
import io
import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock

import cv2
import numpy as np
from sklearn.neighbors import KNeighborsClassifier

from experiments import ablation, evaluate
from image_processing import classifier, preprocessing, train_classifier
from image_processing.errors import PipelineError

SIZE = preprocessing.TARGET_SIZE
PIPELINE_CONFIG = 'Bilateral + CLAHE (pipeline)'


def leaf_image() -> np.ndarray:
    """Ảnh 256x256 như PlantVillage: nền xám, lá xanh, một đốm nâu, thêm nhiễu cố định."""
    image = np.full((256, 256, 3), 128, np.uint8)
    cv2.circle(image, (128, 128), 90, (40, 160, 60), -1)
    cv2.circle(image, (150, 110), 25, (30, 70, 120), -1)
    noise = np.random.default_rng(0).normal(0, 8, image.shape)
    return np.clip(image + noise, 0, 255).astype(np.uint8)


def circle_mask(center, radius) -> np.ndarray:
    mask = np.zeros((SIZE, SIZE), np.uint8)
    cv2.circle(mask, center, radius, 255, -1)
    return mask


LEAF = circle_mask((256, 256), 180)
LESION = circle_mask((300, 220), 50)


class ConfigTests(TestCase):
    def setUp(self):
        self.image = leaf_image()
        self.resized = preprocessing.resize(self.image)

    def test_every_config_returns_preprocessed_size(self):
        for name, prepare in ablation.CONFIGS.items():
            with self.subTest(name):
                out = prepare(self.image)
                self.assertEqual(out.shape, (SIZE, SIZE, 3))
                self.assertEqual(out.dtype, np.uint8)

    def test_pipeline_config_matches_preprocess(self):
        expected, _ = preprocessing.preprocess(self.image)
        np.testing.assert_array_equal(ablation.CONFIGS[PIPELINE_CONFIG](self.image), expected)

    def test_configs_drop_or_replace_one_step(self):
        expected = {
            'Bilateral, bỏ CLAHE': preprocessing.denoise(self.resized),
            'Median thay Bilateral + CLAHE': preprocessing.equalize(
                cv2.medianBlur(self.resized, preprocessing.MEDIAN_KSIZE)),
            'Không lọc nhiễu + CLAHE': preprocessing.equalize(self.resized),
            'Chỉ resize': self.resized,
        }
        for name, image in expected.items():
            with self.subTest(name):
                np.testing.assert_array_equal(ablation.CONFIGS[name](self.image), image)

    def test_configs_differ_from_each_other(self):
        outputs = [prepare(self.image) for prepare in ablation.CONFIGS.values()]
        for i in range(len(outputs)):
            for j in range(i + 1, len(outputs)):
                self.assertFalse(np.array_equal(outputs[i], outputs[j]))


class PredictMasksTests(TestCase):
    def test_seed_is_set_and_prepared_image_is_segmented(self):
        calls = []
        prepared = np.full((SIZE, SIZE, 3), 7, np.uint8)

        def segment_leaf(image):
            calls.append('segment_leaf')
            np.testing.assert_array_equal(image, prepared)
            return LEAF, {}

        with (
            mock.patch.object(ablation.cv2, 'setRNGSeed', side_effect=lambda seed: calls.append(('seed', seed))),
            mock.patch.object(ablation.segmentation, 'segment_leaf', side_effect=segment_leaf),
            mock.patch.object(ablation.segmentation, 'segment_lesions', return_value=(LESION, {})),
        ):
            leaf, lesion = ablation.predict_masks(leaf_image(), lambda image: prepared)
        self.assertEqual(calls, [('seed', ablation.pipeline.RNG_SEED), 'segment_leaf'])
        self.assertIs(leaf, LEAF)
        self.assertIs(lesion, LESION)


class RunAblationTests(TestCase):
    """Ảnh thật ghi ra thư mục tạm; segment_leaf và segment_lesions được thay bằng mask cố định."""

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        path = self.tmp / 'Tomato___Early_blight' / 'lá 1.png'
        path.parent.mkdir()
        cv2.imencode('.png', leaf_image())[1].tofile(str(path))
        self.items = [evaluate.GroundTruth(path, 'Tomato___Early_blight', LEAF, LESION)]
        self.enterContext(mock.patch.object(ablation.segmentation, 'segment_leaf', return_value=(LEAF, {})))
        self.enterContext(mock.patch.object(ablation.segmentation, 'segment_lesions', return_value=(LESION, {})))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def test_one_row_per_image_and_config(self):
        results = ablation.run_ablation(self.items)
        self.assertEqual(list(results), list(ablation.CONFIGS))
        for rows in results.values():
            [row] = rows
            self.assertEqual((row['lop'], row['loi']), ('Early_blight', ''))
            self.assertEqual(row['iou_la'], 1.0)
            self.assertEqual(row['iou_vet_benh'], 1.0)

    def test_error_in_one_config_only_marks_that_config(self):
        def broken(image):
            raise PipelineError('Không tìm thấy lá')

        configs = {'tốt': preprocessing.resize, 'hỏng': broken}
        results = ablation.run_ablation(self.items, configs)
        self.assertEqual(results['tốt'][0]['loi'], '')
        self.assertEqual(results['hỏng'][0]['loi'], 'Không tìm thấy lá')
        self.assertNotIn('iou_la', results['hỏng'][0])

    def test_unreadable_image_marks_every_config(self):
        self.items[0].path.write_bytes(b'khong phai anh')
        results = ablation.run_ablation(self.items)
        for rows in results.values():
            self.assertTrue(rows[0]['loi'])

    def test_main_writes_csv_and_tables(self):
        out = self.tmp / 'ket qua' / 'ablation.csv'
        stdout = io.StringIO()
        with (
            mock.patch.object(evaluate, 'load_ground_truth', return_value=self.items),
            contextlib.redirect_stdout(stdout),
        ):
            self.assertEqual(ablation.main(['--out', str(out)]), 0)
        with open(out, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([row['cau_hinh'] for row in rows], list(ablation.CONFIGS))
        self.assertEqual(rows[0]['iou_la'], '1.0000')
        text = stdout.getvalue()
        for name in ablation.CONFIGS:
            self.assertIn(f'| {name} |', text)
        self.assertIn('| Early_blight |', text)


class ClassifyFeaturesTests(TestCase):
    def setUp(self):
        self.path = Path(self.enterContext(tempfile.TemporaryDirectory())) / 'lá.png'
        cv2.imencode('.png', leaf_image())[1].tofile(str(self.path))

    def test_pipeline_config_matches_train_classifier(self):
        np.testing.assert_array_equal(ablation._classify_features(self.path, ablation.CONFIGS[PIPELINE_CONFIG]),
                                      train_classifier._features_for_path(self.path))

    def test_none_when_leaf_not_found_or_image_unreadable(self):
        with mock.patch.object(ablation.segmentation, 'segment_leaf', side_effect=PipelineError('Không thấy lá')):
            self.assertIsNone(ablation._classify_features(self.path, preprocessing.resize))
        self.path.write_bytes(b'khong phai anh')
        self.assertIsNone(ablation._classify_features(self.path, preprocessing.resize))


class RunClassificationTests(TestCase):
    """Hai lớp, đặc trưng giả bằng chỉ số lớp; ảnh tên 'hong' coi như không tách được lá."""

    CLASSES = ('Tomato___Early_blight', 'Tomato___healthy')

    def setUp(self):
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.object(ablation, 'FEATURES_DIR', tmp / 'cache'))
        self.fake = self.enterContext(mock.patch.object(ablation, '_classify_features', side_effect=self.features))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))  # tiến độ của joblib
        self.train, self.test = [], []
        for cls in self.CLASSES:
            for split, names in ((self.train, ('a', 'b', 'hong')), (self.test, ('c', 'hong'))):
                for name in names:
                    path = tmp / cls / f'{name}_{len(split)}.jpg'
                    path.parent.mkdir(exist_ok=True)
                    path.write_bytes(b'x')
                    split.append(path)
        self.configs = {'chỉ resize': preprocessing.resize}

    def features(self, path, prepare):
        if path.name.startswith('hong'):
            return None
        return np.full(len(classifier.FEATURE_NAMES), float(self.CLASSES.index(path.parent.name)))

    def run_classification(self):
        return ablation.run_classification(self.train, self.test, self.configs, KNeighborsClassifier(1), n_jobs=1)

    def test_skipped_images_dropped_from_train_and_wrong_in_test(self):
        [result] = self.run_classification().values()
        self.assertEqual((result['bo_qua_train'], result['bo_qua_test']), (2, 2))
        self.assertEqual(result['accuracy'], 0.5)
        self.assertEqual(set(result['per_class_f1']), set(self.CLASSES))

    def test_features_are_cached_per_config(self):
        first = self.run_classification()
        calls = self.fake.call_count
        self.assertEqual(calls, len(self.train) + len(self.test))
        self.assertEqual(self.run_classification(), first)
        self.assertEqual(self.fake.call_count, calls)

        self.configs = {'cấu hình khác': preprocessing.resize}
        self.run_classification()
        self.assertEqual(self.fake.call_count, 2 * calls)

    def test_main_classify_writes_json_and_tables(self):
        results = {'chỉ resize': {'accuracy': 0.9, 'macro_f1': 0.8, 'per_class_f1': {self.CLASSES[0]: 0.7},
                                  'bo_qua_train': 1, 'bo_qua_test': 0}}
        out = self.train[0].parent.parent / 'kết quả.json'
        stdout = io.StringIO()
        with (
            mock.patch.object(train_classifier, 'load_split', return_value=[]),
            mock.patch.object(ablation, 'run_classification', return_value=results) as run,
            contextlib.redirect_stdout(stdout),
        ):
            self.assertEqual(ablation.main(['--classify', '--jobs', '2', '--out', str(out)]), 0)
        self.assertEqual(run.call_args.kwargs['n_jobs'], 2)
        self.assertEqual(json.loads(out.read_text(encoding='utf-8')), results)
        self.assertIn('| chỉ resize | 0.900 | 0.800 | 1 / 0 |', stdout.getvalue())
        self.assertIn('| Early_blight | 0.700 |', stdout.getvalue())
