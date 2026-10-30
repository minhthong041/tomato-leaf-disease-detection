"""Test khuyến nghị theo bệnh (api/recommendations.py) và trường disease_recommendation của API."""
import shutil
import tempfile
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from image_processing import classifier, pipeline

from .models import DiagnosisHistory, Disease, User
from .recommendations import DISEASE_RECOMMENDATIONS, PESTICIDE_NOTE, disease_recommendation
from .test_api import make_result, make_upload

MEDIA_ROOT = tempfile.mkdtemp()
HEALTHY = 'Tomato___healthy'
# Khuyến nghị chung theo cấp sai với các lớp này (3D, phần II)
REPLACES_SEVERITY_ADVICE = {
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
    'Tomato___Tomato_mosaic_virus',
    'Tomato___Spider_mites Two-spotted_spider_mite',
    HEALTHY,
}


class RecommendationTableTests(TestCase):
    def test_keys_match_diseases_table(self):
        codes = set(Disease.objects.values_list('code', flat=True))
        self.assertEqual(len(codes), 10)
        self.assertEqual(set(DISEASE_RECOMMENDATIONS), codes)

    def test_keys_cover_classifier_classes(self):
        # Mọi lớp mô hình có thể trả về đều có khuyến nghị
        model = classifier.load_model()
        self.assertEqual(set(model.classes_), set(DISEASE_RECOMMENDATIONS))

    def test_entries_complete(self):
        for code, item in DISEASE_RECOMMENDATIONS.items():
            with self.subTest(code=code):
                self.assertEqual(
                    set(item), {'cause', 'advice', 'sources', 'replaces_severity_advice'},
                )
                self.assertTrue(item['advice'].strip())
                if code == HEALTHY:
                    self.assertIsNone(item['cause'])
                else:
                    self.assertTrue(item['cause'].strip())
                self.assertGreaterEqual(len(item['sources']), 1)
                for title, url in item['sources']:
                    self.assertTrue(title.strip())
                    self.assertTrue(url.startswith('https://'), url)

    def test_replaces_severity_advice(self):
        replaced = {code for code, item in DISEASE_RECOMMENDATIONS.items() if item['replaces_severity_advice']}
        self.assertEqual(replaced, REPLACES_SEVERITY_ADVICE)

    def test_virus_advice_has_no_cure(self):
        for code in ('Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus'):
            self.assertIn('Không có thuốc chữa', DISEASE_RECOMMENDATIONS[code]['advice'])

    def test_api_shape(self):
        data = disease_recommendation('Tomato___Early_blight')
        self.assertEqual(set(data), {'cause', 'advice', 'sources', 'replaces_severity_advice', 'pesticide_note'})
        self.assertEqual(data['sources'][0], {
            'title': 'UC IPM, Early blight', 'url': 'https://ipm.ucanr.edu/agriculture/tomato/Early-Blight',
        })
        self.assertEqual(data['pesticide_note'], PESTICIDE_NOTE)
        self.assertIsNone(disease_recommendation(HEALTHY)['pesticide_note'])
        self.assertIsNone(disease_recommendation('Tomato___khong_co'))


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DiagnosisRecommendationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            'tv4h@example.com', 'mat-khau-thu', fullname='Thành viên 4', terms_accepted_at=timezone.now(),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def post(self, **kwargs):
        with mock.patch.object(pipeline, 'run', **kwargs):
            return self.client.post('/api/diagnoses/', {'image': make_upload()}, format='multipart')

    def test_done_has_both_recommendations(self):
        response = self.post(return_value=make_result())
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.DONE)
        self.assertTrue(response.data['recommendation'])  # theo cấp, giữ nguyên
        self.assertEqual(
            response.data['disease_recommendation'], disease_recommendation('Tomato___Early_blight'),
        )
        # Chi tiết trả cùng dữ liệu; danh sách (trang Lịch sử) không kèm
        detail = self.client.get(f'/api/diagnoses/{response.data["id"]}/')
        self.assertEqual(detail.data['disease_recommendation'], response.data['disease_recommendation'])
        listing = self.client.get('/api/diagnoses/')
        self.assertNotIn('disease_recommendation', listing.data['results'][0])
        self.assertIn('recommendation', listing.data['results'][0])
        # PATCH đánh dấu vẫn trả đủ
        patched = self.client.patch(f'/api/diagnoses/{response.data["id"]}/', {'is_bookmarked': True}, format='json')
        self.assertEqual(patched.data['disease_recommendation'], response.data['disease_recommendation'])

    def test_virus_replaces_severity_advice(self):
        result = make_result(disease_code='Tomato___Tomato_mosaic_virus')
        response = self.post(return_value=result)
        self.assertTrue(response.data['disease_recommendation']['replaces_severity_advice'])

    def test_failed_has_no_disease_recommendation(self):
        response = self.post(side_effect=pipeline.PipelineError('Không tìm thấy lá trong ảnh.'))
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.FAILED)
        self.assertIsNone(response.data['disease_recommendation'])
