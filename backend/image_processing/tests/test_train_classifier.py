"""Unit tests cho quy trình huấn luyện SVM."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from image_processing import train_classifier as training


class TestLoadSplit(unittest.TestCase):
    def test_load_split_preserves_spaces_and_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            splits = root / "splits"
            splits.mkdir()
            relative = "plantvillage/Tomato___healthy/image with spaces.JPG"
            (splits / "train.txt").write_text(relative + "\n", encoding="utf-8-sig")
            with (
                patch.object(training, "DATASET_DIR", root),
                patch.object(training, "SPLITS_DIR", splits),
            ):
                paths = training.load_split("train")
            self.assertEqual(paths, [root / relative])

    def test_invalid_split(self):
        with self.assertRaises(ValueError):
            training.load_split("validation")


class TestLeafMaskFor(unittest.TestCase):
    def test_returns_segmentation_mask(self):
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        expected = np.zeros((16, 16), dtype=np.uint8)
        expected[2:14, 2:14] = 255
        with patch.object(
            training.segmentation,
            "segment_leaf",
            return_value=(expected, {}),
        ) as mock_segment:
            actual = training.leaf_mask_for(image)
        mock_segment.assert_called_once_with(image)
        np.testing.assert_array_equal(actual, expected)

    def test_rejects_invalid_mask_values(self):
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        invalid = np.full((16, 16), 128, dtype=np.uint8)
        with patch.object(
            training.segmentation, "segment_leaf", return_value=(invalid, {})
        ):
            with self.assertRaises(ValueError):
                training.leaf_mask_for(image)

    def test_rejects_empty_mask(self):
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        empty = np.zeros((16, 16), dtype=np.uint8)
        with patch.object(
            training.segmentation, "segment_leaf", return_value=(empty, {})
        ):
            with self.assertRaises(ValueError):
                training.leaf_mask_for(image)

    def test_no_temporary_mask_fallback(self):
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        with patch.object(
            training.segmentation,
            "segment_leaf",
            side_effect=NotImplementedError,
        ):
            with self.assertRaises(NotImplementedError):
                training.leaf_mask_for(image)

    def test_temp_threshold_removed(self):
        self.assertFalse(hasattr(training, "TEMP_S_THRESHOLD"))

    def test_does_not_hide_segmentation_errors(self):
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        with patch.object(
            training.segmentation,
            "segment_leaf",
            side_effect=ValueError("segmentation failed"),
        ):
            with self.assertRaisesRegex(ValueError, "segmentation failed"):
                training.leaf_mask_for(image)


class TestBuildFeatures(unittest.TestCase):
    # Các test patch hàm trong module nên chạy với n_jobs=1 (cùng tiến trình):
    # tiến trình con của joblib không thấy các patch này.

    def test_build_features_shape_and_labels(self):
        paths = [
            Path("dataset/Class_A/image one.JPG"),
            Path("dataset/Class_B/image two.JPG"),
        ]
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        mask = np.full((16, 16), 255, dtype=np.uint8)
        vector = np.arange(14, dtype=np.float64)
        with (
            patch.object(training, "load_image", return_value=image),
            patch.object(
                training.preprocessing,
                "preprocess",
                return_value=(image, {}),
            ),
            patch.object(training, "leaf_mask_for", return_value=mask),
            patch.object(
                training.classifier,
                "extract_features",
                return_value=vector,
            ),
        ):
            X, y = training.build_features(paths, split=None, use_cache=False, n_jobs=1)
        self.assertEqual(X.shape, (2, 14))
        self.assertEqual(y.shape, (2,))
        self.assertEqual(list(y), ["Class_A", "Class_B"])
        self.assertEqual(X.dtype, np.float64)

    def test_preserves_path_order(self):
        paths = [
            Path("dataset/Class_A/a.JPG"),
            Path("dataset/Class_B/b.JPG"),
            Path("dataset/Class_C/c.JPG"),
        ]
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        mask = np.full((16, 16), 255, dtype=np.uint8)
        vectors = [np.full(14, value, dtype=np.float64) for value in (1, 2, 3)]
        with (
            patch.object(training, "load_image", return_value=image),
            patch.object(
                training.preprocessing,
                "preprocess",
                return_value=(image, {}),
            ),
            patch.object(training, "leaf_mask_for", return_value=mask),
            patch.object(
                training.classifier,
                "extract_features",
                side_effect=vectors,
            ),
        ):
            X, y = training.build_features(paths, split=None, use_cache=False, n_jobs=1)
        self.assertEqual(list(y), ["Class_A", "Class_B", "Class_C"])
        np.testing.assert_array_equal(X[:, 0], [1, 2, 3])

    def test_rejects_empty_paths(self):
        with self.assertRaises(ValueError):
            training.build_features([], use_cache=False)

    def test_reports_failed_image(self):
        paths = [Path("dataset/Class_A/broken.JPG")]
        with patch.object(
            training, "load_image", side_effect=ValueError("Cannot decode image")
        ):
            with self.assertRaisesRegex(RuntimeError, "broken.JPG"):
                training.build_features(paths, split=None, use_cache=False, n_jobs=1)

    def test_rejects_wrong_feature_length(self):
        path = Path("dataset/Class_A/short.JPG")
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        mask = np.full((16, 16), 255, dtype=np.uint8)
        with (
            patch.object(training, "load_image", return_value=image),
            patch.object(
                training.preprocessing,
                "preprocess",
                return_value=(image, {}),
            ),
            patch.object(training, "leaf_mask_for", return_value=mask),
            patch.object(
                training.classifier,
                "extract_features",
                return_value=np.zeros(5, dtype=np.float64),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "short.JPG"):
                training._features_for_path(path)

    def test_fixes_opencv_seed_per_image(self):
        with (
            patch.object(training.cv2, "setRNGSeed") as set_seed,
            patch.object(training, "load_image", side_effect=ValueError("stop")),
        ):
            with self.assertRaises(RuntimeError):
                training._features_for_path(Path("dataset/Class_A/a.JPG"))
        set_seed.assert_called_once_with(training.FEATURE_RNG_SEED)

    def test_cache_is_reused_and_invalidated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "Class_A" / "image.JPG"
            image_path.parent.mkdir()
            image_path.write_bytes(b"mock image")
            image = np.zeros((16, 16, 3), dtype=np.uint8)
            mask = np.full((16, 16), 255, dtype=np.uint8)
            vector = np.arange(14, dtype=np.float64)
            with (
                patch.object(training, "OUTPUT_DIR", root),
                patch.object(training, "load_image", return_value=image) as loader,
                patch.object(
                    training.preprocessing,
                    "preprocess",
                    return_value=(image, {}),
                ),
                patch.object(training, "leaf_mask_for", return_value=mask),
                patch.object(
                    training.classifier,
                    "extract_features",
                    return_value=vector,
                ),
            ):
                first_X, first_y = training.build_features(
                    [image_path], split="smoke", n_jobs=1
                )
                second_X, second_y = training.build_features(
                    [image_path], split="smoke", n_jobs=1
                )
                self.assertEqual(loader.call_count, 1)
                np.testing.assert_array_equal(first_X, second_X)
                np.testing.assert_array_equal(first_y, second_y)

                image_path.write_bytes(b"updated mock image")
                training.build_features([image_path], split="smoke", n_jobs=1)
                self.assertEqual(loader.call_count, 2)


class TrainEvaluateTests(unittest.TestCase):
    """Kiểm thử huấn luyện và đánh giá bộ phân loại."""

    def setUp(self):
        rng = np.random.default_rng(42)
        self.X = np.vstack(
            [
                rng.normal(0, 0.5, size=(20, 14)),
                rng.normal(3, 0.5, size=(20, 14)),
            ]
        )
        self.y = np.array(["Class_A"] * 20 + ["Class_B"] * 20)

    def test_train_returns_fitted_model(self):
        model = training.train(self.X, self.y)
        self.assertEqual(list(model.classes_), ["Class_A", "Class_B"])

    def test_train_supports_predict_proba(self):
        model = training.train(self.X, self.y)
        probabilities = model.predict_proba(self.X[:3])
        self.assertEqual(probabilities.shape, (3, 2))
        self.assertTrue(np.isfinite(probabilities).all())
        np.testing.assert_allclose(probabilities.sum(axis=1), np.ones(3))

    def test_train_rejects_invalid_feature_shape(self):
        with self.assertRaises(ValueError):
            training.train(self.X[:, :10], self.y)

    def test_train_rejects_single_class(self):
        with self.assertRaises(ValueError):
            training.train(self.X[:20], self.y[:20])

    def test_evaluate_returns_metrics(self):
        model = training.train(self.X, self.y)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            metrics = training.evaluate(model, self.X, self.y, output_dir)
            self.assertIn("accuracy", metrics)
            self.assertIn("macro_f1", metrics)
            self.assertIn("per_class_f1", metrics)
            self.assertGreaterEqual(metrics["accuracy"], 0)
            self.assertLessEqual(metrics["accuracy"], 1)
            self.assertTrue((output_dir / "confusion_matrix.png").is_file())


if __name__ == "__main__":
    unittest.main()
