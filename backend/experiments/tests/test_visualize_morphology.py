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
        self.image = np.full((96, 96, 3), (0, 170, 0), dtype=np.uint8)
        self.leaf = np.zeros((96, 96), dtype=np.uint8)
        cv2.ellipse(self.leaf, (48, 48), (35, 30), 0, 0, 360, 255, -1)
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
            ('correct-positive', self.raw_lesion, self.raw_lesion),
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
        output = self.tmp / 'examples.png'

        visualize_morphology.plot_examples(cases, output)

        self.assert_png(output)
