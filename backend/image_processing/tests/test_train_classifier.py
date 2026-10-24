"""Test 3B không cần dataset hoặc model thật."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from image_processing import train_classifier as tc


class TrainClassifierTests(unittest.TestCase):
    def test_train_has_predict_proba(self):
        rng = np.random.default_rng(42)
        X = np.vstack([rng.normal(-2, 0.2, (10, 14)), rng.normal(2, 0.2, (10, 14))])
        y = np.array(["class_a"] * 10 + ["class_b"] * 10)
        model = tc.train(X, y)
        probabilities = model.predict_proba(X[:3])
        self.assertEqual(probabilities.shape, (3, 2))
        self.assertTrue(np.isfinite(probabilities).all())
        self.assertTrue(((probabilities >= 0) & (probabilities <= 1)).all())
        np.testing.assert_allclose(probabilities.sum(axis=1), np.ones(3))

    def test_train_classes_match_labels(self):
        rng = np.random.default_rng(42)
        X = rng.normal(size=(20, 14))
        y = np.array(["class_b"] * 10 + ["class_a"] * 10)
        model = tc.train(X, y)
        np.testing.assert_array_equal(model.classes_, ["class_a", "class_b"])

    def test_load_split_keeps_spaces_and_handles_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "dataset"
            splits = dataset / "splits"
            splits.mkdir(parents=True)
            relative = "plantvillage/class with spaces/leaf image.jpg"
            (splits / "train.txt").write_text(relative + "\n\n", encoding="utf-8-sig")
            with patch.object(tc, "DATASET_DIR", dataset), patch.object(
                tc, "SPLITS_DIR", splits
            ):
                self.assertEqual(tc.load_split("train"), [dataset / relative])

    def test_auto_falls_back_only_for_not_implemented(self):
        image = np.zeros((8, 8, 3), dtype=np.uint8)
        mask = np.full((8, 8), 255, dtype=np.uint8)
        with patch.object(tc, "MASK_MODE", "auto"), patch.object(
            tc.segmentation, "segment_leaf", side_effect=NotImplementedError
        ), patch.object(tc, "_temporary_mask", return_value=mask) as temporary:
            np.testing.assert_array_equal(tc.leaf_mask_for(image), mask)
            temporary.assert_called_once_with(image)

    def test_temp_mode_does_not_call_tv2(self):
        image = np.zeros((8, 8, 3), dtype=np.uint8)
        mask = np.full((8, 8), 255, dtype=np.uint8)
        with patch.object(tc, "MASK_MODE", "temp"), patch.object(
            tc.segmentation, "segment_leaf"
        ) as segment, patch.object(tc, "_temporary_mask", return_value=mask):
            np.testing.assert_array_equal(tc.leaf_mask_for(image), mask)
            segment.assert_not_called()

    def test_auto_does_not_hide_segmentation_errors(self):
        image = np.zeros((8, 8, 3), dtype=np.uint8)
        with patch.object(tc, "MASK_MODE", "auto"), patch.object(
            tc.segmentation, "segment_leaf", side_effect=ValueError("test")
        ):
            with self.assertRaises(ValueError):
                tc.leaf_mask_for(image)
