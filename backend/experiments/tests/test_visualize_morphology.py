import tempfile
from pathlib import Path
from unittest import TestCase

import cv2
import matplotlib
import numpy as np

from experiments import evaluate, visualize_morphology


class MorphologyFigureTests(TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.image = np.full((96, 96, 3), 255, dtype=np.uint8)
        cv2.ellipse(
            self.image, (48, 48), (35, 30), 0, 0, 360, (0, 170, 0), -1,
        )
        self.leaf = visualize_morphology._leaf_segmentation_stages(
            self.image,
        )[-1]
        self.raw_lesion = np.zeros_like(self.leaf)
        cv2.circle(self.raw_lesion, (48, 48), 8, 255, -1)
        self.lesion = self.raw_lesion.copy()

    def assert_png(self, path):
        self.assertTrue(path.is_file())
        self.assertIsNotNone(
            cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR),
        )

    def test_matplotlib_uses_agg_backend(self):
        self.assertEqual(matplotlib.get_backend().lower(), 'agg')

    def test_plot_morphology_writes_figure(self):
        output = self.tmp / 'morphology.png'

        visualize_morphology.plot_morphology(
            self.image, self.leaf, self.raw_lesion, self.lesion, output,
        )

        self.assert_png(output)

    def test_plot_examples_shows_correct_and_incorrect_cases(self):
        empty = np.zeros_like(self.leaf)
        false_positive = self.raw_lesion.copy()
        cases = []
        for name, truth, prediction in (
            ('highest-iou', self.raw_lesion, self.raw_lesion),
            (
                'lowest-iou', self.raw_lesion,
                cv2.circle(empty.copy(), (20, 20), 5, 255, -1),
            ),
            ('false-positive', empty, false_positive),
            ('correct-negative', empty, empty),
        ):
            item = evaluate.GroundTruth(
                self.tmp / f'{name}.jpg', 'Tomato___Early_blight',
                self.leaf, truth,
            )
            metrics = evaluate.evaluate_image(
                self.leaf, truth, self.leaf, prediction,
            )
            cases.append(
                visualize_morphology.Example(
                    item, self.image, prediction, metrics,
                ),
            )

        selected = visualize_morphology._select_examples(cases)
        self.assertEqual(
            [label for label, _ in selected],
            [
                'IoU cao nhất', 'IoU thấp nhất',
                'Báo nhầm (mask chuẩn rỗng)', 'Đúng âm (mask chuẩn rỗng)',
            ],
        )
        self.assertEqual(selected[0][1].item.path.stem, 'highest-iou')
        self.assertEqual(selected[1][1].item.path.stem, 'lowest-iou')

        output = self.tmp / 'examples.png'

        visualize_morphology.plot_examples(cases, output)

        self.assert_png(output)

    def test_examples_overlay_uses_evaluate_colors_and_pixel_rules(self):
        truth = np.zeros_like(self.leaf)
        prediction = np.zeros_like(self.leaf)
        truth[10, 10] = 255
        truth[10, 11] = 255
        prediction[10, 10] = 255
        prediction[10, 12] = 255

        expected = cv2.cvtColor(
            evaluate.color_comparison(self.image, prediction, truth),
            cv2.COLOR_BGR2RGB,
        )
        actual = visualize_morphology._examples_overlay(
            self.image, truth, prediction,
        )

        np.testing.assert_array_equal(actual, expected)
