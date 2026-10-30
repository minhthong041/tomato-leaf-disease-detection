import csv
import tempfile
from pathlib import Path
from unittest import TestCase, mock

import cv2
import numpy as np

from experiments import pick_demo_images as demo
from image_processing import pipeline
from image_processing.errors import PipelineError

EARLY = 'Tomato___Early_blight'
MOSAIC = 'Tomato___Tomato_mosaic_virus'


def row(true, pred, confidence, level=2, error=''):
    data = {'anh_goc': f'plantvillage/{true}/a.jpg', 'lop_that': true, 'loi': error}
    if not error:
        data.update(du_doan=pred, do_tin_cay=confidence, cap=level,
                    canh_bao=demo.warnings_for(pred, confidence, level))
    return data


class WarningRuleTests(TestCase):
    def test_same_rules_as_frontend(self):
        self.assertEqual(demo.warnings_for(EARLY, 0.9, 2), [])
        self.assertEqual(demo.warnings_for(EARLY, 0.5, 2), ['do_tin_cay_thap'])
        self.assertEqual(demo.warnings_for(demo.HEALTHY_CODE, 0.9, 1), ['la_khoe_co_vet_benh'])
        self.assertEqual(demo.warnings_for(demo.HEALTHY_CODE, 0.9, 0), [])
        self.assertEqual(demo.warnings_for(EARLY, 0.9, 0), ['benh_nhung_cap_0'])
        # Bệnh virus không có đốm: Cấp 0 là bình thường
        self.assertEqual(demo.warnings_for(MOSAIC, 0.9, 0), [])

    def test_threshold_matches_frontend(self):
        source = (demo.BACKEND_DIR.parent / 'frontend' / 'src' / 'constants' / 'diagnosis.js').read_text('utf-8')
        self.assertIn(f'LOW_CONFIDENCE_THRESHOLD = {demo.LOW_CONFIDENCE_THRESHOLD};', source)
        for code in demo.NO_LESION_DISEASE_CODES:
            self.assertIn(f"'{code}'", source)


class PickTests(TestCase):
    def test_class_image_is_correct_without_warning(self):
        rows = [
            row(EARLY, EARLY, 0.99, level=0),           # cảnh báo "bệnh nhưng Cấp 0"
            row(EARLY, MOSAIC, 0.98),                   # đoán sai
            row(EARLY, EARLY, 0.80),
            row(EARLY, EARLY, 0.85),
            row(EARLY, '', 0, error='Không tìm thấy lá'),
        ]
        self.assertEqual(demo.pick_class_image(rows)['do_tin_cay'], 0.85)
        self.assertIsNone(demo.pick_class_image(rows[:2]))

    def test_low_confidence_prefers_wrong_prediction(self):
        rows = [row(EARLY, EARLY, 0.50), row(EARLY, MOSAIC, 0.40), row(EARLY, MOSAIC, 0.30), row(EARLY, EARLY, 0.9)]
        picked = demo.pick_low_confidence(rows)
        self.assertEqual((picked['du_doan'], picked['do_tin_cay']), (MOSAIC, 0.40))
        self.assertIsNone(demo.pick_low_confidence(rows[3:]))


class LoadAsWebTests(TestCase):
    def test_same_pixels_as_upload_api(self):
        # Ảnh lưu lại JPG như khi tải lên web: điểm ảnh khác file gốc nhưng cùng kích thước
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'lá thử.jpg'
            rng = np.random.default_rng(0)
            original = rng.integers(0, 255, (32, 48, 3), np.uint8)
            cv2.imencode('.jpg', original, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tofile(str(path))
            image = demo.load_as_web(path)
            raw = pipeline.load_image(path)
        self.assertEqual(image.shape, raw.shape)
        self.assertFalse(np.array_equal(image, raw))

    def test_unreadable_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'hong.jpg'
            path.write_bytes(b'khong phai anh')
            with self.assertRaises(Exception):
                demo.load_as_web(path)


class UnusableImageTests(TestCase):
    def test_pipeline_rejects_it(self):
        with self.assertRaises(PipelineError):
            pipeline.run(demo.make_unusable_image())


class MainTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        lines = []
        for code in (EARLY, MOSAIC):
            for index in range(3):
                path = self.root / 'plantvillage' / code / f'anh {index}.JPG'
                path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imencode('.jpg', np.full((8, 8, 3), index, np.uint8))[1].tofile(str(path))
                lines.append(f'plantvillage/{code}/anh {index}.JPG')
        self.split = self.root / 'test.txt'
        self.split.write_text('\n'.join(lines), encoding='utf-8')

    def fake_diagnose(self, path):
        index = int(path.stem[-1])
        code = path.parent.name
        if index == 2:
            return {**row(code, MOSAIC if code == EARLY else EARLY, 0.4), 'anh_goc': f'plantvillage/{code}/{path.name}'}
        return {**row(code, code, 0.7 + index / 10), 'anh_goc': f'plantvillage/{code}/{path.name}'}

    def test_writes_images_and_csv(self):
        out = self.root / 'demo'
        with mock.patch.object(demo, 'DATASET_DIR', self.root), \
                mock.patch.object(demo, 'TEST_SPLIT', self.split), \
                mock.patch.object(demo, 'diagnose', side_effect=self.fake_diagnose):
            self.assertEqual(demo.main(['--per-class', '3', '--out', str(out)]), 0)
        names = sorted(p.name for p in out.iterdir())
        self.assertEqual(names, [
            '01_Early_blight.jpg', '02_Tomato_mosaic_virus.jpg', '11_do_tin_cay_thap.jpg',
            demo.UNUSABLE_NAME, 'demo_images.csv',
        ])
        with open(out / 'demo_images.csv', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]['anh_goc'], f'plantvillage/{EARLY}/anh 1.JPG')  # độ tin cậy 0,8 > 0,7
        self.assertEqual(rows[2]['canh_bao'], 'do_tin_cay_thap')
        self.assertIn('Không tìm thấy lá', rows[3]['loi'])

    def test_skips_missing_images(self):
        (self.root / 'plantvillage' / EARLY / 'anh 1.JPG').unlink()
        out = self.root / 'demo'
        with mock.patch.object(demo, 'DATASET_DIR', self.root), \
                mock.patch.object(demo, 'TEST_SPLIT', self.split), \
                mock.patch.object(demo, 'diagnose', side_effect=self.fake_diagnose) as diagnose:
            self.assertEqual(demo.main(['--per-class', '3', '--out', str(out)]), 0)
        tried = {call.args[0].name for call in diagnose.call_args_list if call.args[0].parent.name == EARLY}
        self.assertEqual(tried, {'anh 0.JPG', 'anh 2.JPG'})

    def test_missing_dataset(self):
        with mock.patch.object(demo, 'DATASET_DIR', self.root / 'khong_co'), \
                mock.patch.object(demo, 'TEST_SPLIT', self.split):
            self.assertEqual(demo.main(['--out', str(self.root / 'demo')]), 1)
