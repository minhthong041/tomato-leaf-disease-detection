import tempfile
from pathlib import Path
from unittest import TestCase, mock

import cv2
import numpy as np

from experiments import evaluate, histogram_clahe
from image_processing import preprocessing

SIZE = preprocessing.TARGET_SIZE


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


class FigureTests(TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.image_path = self.tmp / 'Tomato___Early_blight' / 'lá.jpg'
        self.image_path.parent.mkdir()
        cv2.imencode('.jpg', leaf_image())[1].tofile(str(self.image_path))

    def assert_png(self, path):
        self.assertTrue(path.is_file())
        self.assertIsNotNone(cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR))

    def test_plot_clahe_writes_figure(self):
        out = self.tmp / 'clahe' / 'a.png'
        std_before, std_after = histogram_clahe.plot_clahe(self.image_path, out, circle_mask((256, 256), 180))
        self.assert_png(out)
        self.assertGreater(std_before, 0)
        self.assertGreater(std_after, 0)

    def test_compare_denoise_with_and_without_mask(self):
        for mask in (circle_mask((300, 220), 50), None):
            with self.subTest(mask=mask is not None):
                out = self.tmp / 'denoise' / f'{mask is not None}.png'
                metrics = histogram_clahe.compare_denoise(self.image_path, out, mask)
                self.assert_png(out)
                self.assertEqual(set(metrics), {'bilateral', 'median'})
                for kept_edge, kept_flat, ratio in metrics.values():
                    self.assertTrue(0 < kept_edge and 0 < kept_flat)
                    self.assertAlmostEqual(ratio, kept_edge / kept_flat, places=5) # gradient tính bằng float32


class ZoomBoxTests(TestCase):
    def test_box_stays_inside_image_near_corner(self):
        edge = np.zeros((SIZE, SIZE), bool)
        edge[2, 2] = True
        x, y, w, h = histogram_clahe.zoom_box(edge, np.ones((SIZE, SIZE), np.float32))
        self.assertEqual((x, y, w, h), (0, 0, histogram_clahe.ZOOM_SIZE, histogram_clahe.ZOOM_SIZE))

    def test_box_covers_strongest_edge(self):
        edge = np.zeros((SIZE, SIZE), bool)
        edge[100, 100] = edge[400, 300] = True
        strength = np.ones((SIZE, SIZE), np.float32)
        strength[400, 300] = 10
        x, y, w, h = histogram_clahe.zoom_box(edge, strength)
        self.assertTrue(x <= 300 < x + w and y <= 400 < y + h)


class EdgeMetricsTests(TestCase):
    def test_unfiltered_image_keeps_everything(self):
        image = preprocessing.resize(leaf_image())
        edge = histogram_clahe._edge_band(circle_mask((256, 256), 180))
        self.assertEqual(histogram_clahe.edge_metrics(image, image, edge), (1.0, 1.0, 1.0))


class MainTests(TestCase):
    def test_one_figure_per_class(self):
        empty = np.zeros((SIZE, SIZE), np.uint8)
        leaf = circle_mask((256, 256), 180)
        items = [
            evaluate.GroundTruth(Path(f'dataset/plantvillage/{cls}/{name}.jpg'), cls, leaf, lesion)
            for cls, name, lesion in (
                ('Tomato___Early_blight', 'a', circle_mask((300, 220), 50)),
                ('Tomato___Early_blight', 'b', empty),
                ('Tomato___healthy', 'c', empty),
            )
        ]
        metrics = {'bilateral': (0.6, 0.4, 1.5), 'median': (0.6, 0.5, 1.2)}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(evaluate, 'load_ground_truth', return_value=items), \
                mock.patch.object(histogram_clahe, 'plot_clahe', return_value=(30.0, 50.0)) as plot_clahe, \
                mock.patch.object(histogram_clahe, 'compare_denoise', return_value=metrics) as compare_denoise, \
                mock.patch('builtins.print'):
            self.assertEqual(histogram_clahe.main(['--out', tmp]), 0)

        self.assertEqual(
            [call.args[1].name for call in plot_clahe.call_args_list], ['01_Early_blight.png', '02_healthy.png'],
        )
        # Ảnh có vết bệnh xét mép vết bệnh, ảnh không có vết bệnh xét mép lá
        (_, _, mask_1, name_1), (_, _, mask_2, name_2) = [call.args for call in compare_denoise.call_args_list]
        self.assertIs(mask_1, items[0].lesion_mask)
        self.assertEqual(name_1, 'vết bệnh')
        self.assertIs(mask_2, items[2].leaf_mask)
        self.assertEqual(name_2, 'lá')
