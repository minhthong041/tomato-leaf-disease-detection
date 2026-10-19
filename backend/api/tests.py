from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from image_processing import steps
from image_processing.severity import IPM_RECOMMENDATIONS

from .models import DiagnosisHistory, DiagnosisStep, Disease, User

Level = DiagnosisHistory.SeverityLevel


class DiagnosisConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            'tv1@example.com', 'mat-khau-thu', fullname='Thành viên 1',
            terms_accepted_at=timezone.now(),
        )
        # Các lớp bệnh có sẵn từ migration 0004_seed_diseases
        cls.early_blight = Disease.objects.get(code='Tomato___Early_blight')
        cls.healthy = Disease.objects.get(code='Tomato___healthy')

    def make_history(self, **fields):
        # Gán đường dẫn có sẵn -> không đọc file, không qua bước xóa EXIF
        return DiagnosisHistory.objects.create(
            user=self.user, original_image='uploads/thu.jpg', **fields,
        )

    def done_fields(self, **overrides):
        fields = {
            'status': DiagnosisHistory.Status.DONE,
            'disease': self.early_blight,
            'disease_confidence': Decimal('0.9100'),
            'severity_level': Level.MODERATE,
            'leaf_area_px': 10000,
            'lesion_area_px': 850,
            'infected_ratio': Decimal('0.0850'),
            'lesion_count': 3,
        }
        fields.update(overrides)
        return fields

    def assertViolates(self, **fields):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_history(**fields)

    def test_done_with_full_result(self):
        history = self.make_history(**self.done_fields())
        self.assertEqual(history.get_severity_level_display(), 'Cấp 2 - Trung bình')

    def test_done_requires_disease(self):
        self.assertViolates(**self.done_fields(disease=None))

    def test_done_requires_confidence(self):
        self.assertViolates(**self.done_fields(disease_confidence=None))

    def test_done_requires_severity_level(self):
        self.assertViolates(**self.done_fields(severity_level=None))

    def test_pending_without_result(self):
        self.make_history()

    def test_level_above_4(self):
        self.assertViolates(**self.done_fields(severity_level=5))

    def test_confidence_above_1(self):
        self.assertViolates(**self.done_fields(disease_confidence=Decimal('1.5000')))

    def test_level_0_requires_no_lesion(self):
        self.assertViolates(**self.done_fields(severity_level=Level.HEALTHY))

    def test_lesion_requires_level_above_0(self):
        self.assertViolates(**self.done_fields(
            severity_level=Level.MILD, lesion_area_px=0, infected_ratio=Decimal('0'), lesion_count=0,
        ))

    def test_healthy_leaf(self):
        self.make_history(**self.done_fields(
            disease=self.healthy, severity_level=Level.HEALTHY,
            lesion_area_px=0, infected_ratio=Decimal('0'), lesion_count=0,
        ))

    def test_only_one_healthy_disease(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Disease.objects.create(code='Tomato___healthy_2', name='Lá khỏe 2', is_healthy=True)

    def test_step_unique_per_history(self):
        history = self.make_history()
        DiagnosisStep.objects.create(history=history, step=DiagnosisStep.Step.LEAF_MASK, image='steps/a.png')
        with self.assertRaises(IntegrityError), transaction.atomic():
            DiagnosisStep.objects.create(history=history, step=DiagnosisStep.Step.LEAF_MASK, image='steps/b.png')

    def test_disease_in_use_cannot_be_deleted(self):
        self.make_history(**self.done_fields())
        with self.assertRaises(ProtectedError):
            self.early_blight.delete()


class SeededDiseaseTests(TestCase):
    """Migration 0004_seed_diseases nạp đủ 10 lớp lá cà chua của PlantVillage."""

    def test_ten_tomato_classes(self):
        codes = set(Disease.objects.values_list('code', flat=True))
        self.assertEqual(codes, {
            'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight',
            'Tomato___Leaf_Mold', 'Tomato___Septoria_leaf_spot',
            'Tomato___Spider_mites Two-spotted_spider_mite', 'Tomato___Target_Spot',
            'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus', 'Tomato___healthy',
        })

    def test_only_healthy_class_is_healthy(self):
        self.assertEqual(
            list(Disease.objects.filter(is_healthy=True).values_list('code', flat=True)),
            ['Tomato___healthy'],
        )


class PipelineSchemaMatchTests(TestCase):
    """Pipeline (image_processing) và database phải dùng cùng tên bước và cùng thang cấp độ."""

    def test_step_names(self):
        self.assertEqual(steps.ORDER, tuple(DiagnosisStep.Step.values))

    def test_severity_levels(self):
        self.assertEqual(sorted(IPM_RECOMMENDATIONS), Level.values)
