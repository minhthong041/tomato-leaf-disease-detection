"""Test API chẩn đoán. pipeline.run được thay bằng hàm giả, nên chạy được khi các giai đoạn 1–4 chưa cài đặt."""
import shutil
import tempfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest import mock

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from image_processing import pipeline, steps
from image_processing.severity import IPM_RECOMMENDATIONS

from . import diagnosis as diagnosis_service
from .models import DiagnosisHistory, DiagnosisStep, User

URL = '/api/diagnoses/'
SIZE = 32
MEDIA_ROOT = tempfile.mkdtemp()
# Lần mã hóa thứ 4 lỗi: ảnh kết quả + 2 ảnh bước đã ghi xuống media trước đó
FAIL_ON_ENCODE = 4


def list_files(media_root, folder):
    """Các file (kể cả trong thư mục con YYYY/MM) dưới media_root/folder."""
    return [path for path in Path(media_root, folder).rglob('*') if path.is_file()]


def make_upload(fmt='PNG', name='la.png'):
    buffer = BytesIO()
    Image.new('RGB', (SIZE, SIZE), (40, 160, 60)).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{fmt.lower()}')


def make_result(**overrides):
    image = np.zeros((SIZE, SIZE, 3), np.uint8)
    fields = {
        'disease_code': 'Tomato___Early_blight',
        'disease_confidence': 0.8765,
        'severity_level': 2,
        'leaf_area_px': 1600,
        'lesion_area_px': 100,
        'infected_ratio': 0.0625,
        'lesion_count': 1,
        # Kiểu numpy như khi TV2 dùng cv2.contourArea / np.mean -> phải lưu được vào JSONField
        'lesions': [{
            'area': np.int64(100), 'perimeter': np.float64(40.0), 'circularity': 0.785,
            'center': [np.int32(25), 25], 'bbox': [20, 20, 10, 10],
        }],
        'processed_image': image,
        'steps': {name: image for name in steps.ORDER},
    }
    fields.update(overrides)
    return pipeline.PipelineResult(**fields)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DiagnosisApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            'tv4@example.com', 'mat-khau-thu', fullname='Thành viên 4', terms_accepted_at=timezone.now(),
        )
        cls.other = User.objects.create_user(
            'khac@example.com', 'mat-khau-thu', fullname='Người khác', terms_accepted_at=timezone.now(),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def post_image(self, result=None, side_effect=None, upload=None):
        with mock.patch.object(pipeline, 'run', return_value=result, side_effect=side_effect) as run:
            response = self.client.post(URL, {'image': upload or make_upload()}, format='multipart')
        return response, run

    # ---------- POST /api/diagnoses/ ----------

    def test_create_done(self):
        response, run = self.post_image(make_result())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data
        self.assertEqual(data['status'], DiagnosisHistory.Status.DONE)
        self.assertEqual(data['disease'], {
            'code': 'Tomato___Early_blight', 'name': data['disease']['name'], 'is_healthy': False,
        })
        self.assertEqual(data['disease_confidence'], '0.8765')
        self.assertEqual(data['infected_ratio'], '0.0625')
        self.assertEqual(data['severity_level'], 2)
        self.assertEqual(data['recommendation'], IPM_RECOMMENDATIONS[2])
        self.assertEqual((data['leaf_area_px'], data['lesion_area_px'], data['lesion_count']), (1600, 100, 1))
        self.assertEqual(data['lesions'][0]['area'], 100)
        self.assertIsNone(data['error_message'])
        self.assertFalse(data['is_bookmarked'])
        # URL ảnh đầy đủ để frontend dùng thẳng trong <img>
        self.assertTrue(data['original_image'].startswith('http://testserver/media/uploads/'))
        self.assertTrue(data['processed_image'].startswith('http://testserver/media/results/'))
        self.assertEqual([item['step'] for item in data['steps']], list(steps.ORDER))
        self.assertTrue(data['steps'][0]['image'].startswith('http://testserver/media/steps/'))

        # Pipeline nhận ảnh BGR uint8 giải mã từ ảnh đã lưu
        image = run.call_args.args[0]
        self.assertEqual((image.dtype, image.shape), (np.uint8, (SIZE, SIZE, 3)))
        self.assertEqual(tuple(image[0, 0]), (60, 160, 40))  # RGB (40, 160, 60) -> BGR

        history = DiagnosisHistory.objects.get(pk=data['id'])
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.steps.count(), len(steps.ORDER))

    def test_create_healthy_leaf(self):
        result = make_result(
            disease_code='Tomato___healthy', severity_level=0, lesion_area_px=0,
            infected_ratio=0.0, lesion_count=0, lesions=[],
        )
        response, _ = self.post_image(result)
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.DONE)
        self.assertTrue(response.data['disease']['is_healthy'])
        self.assertEqual(response.data['infected_ratio'], '0.0000')
        self.assertEqual(response.data['recommendation'], IPM_RECOMMENDATIONS[0])

    def test_jpeg_accepted(self):
        response, _ = self.post_image(make_result(), upload=make_upload('JPEG', 'la.jpg'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_image_error_is_shown_to_user(self):
        # Lỗi do ảnh (PipelineError): lưu failed, thông báo nguyên văn
        response, _ = self.post_image(side_effect=pipeline.PipelineError('Không tìm thấy lá trong ảnh.'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.FAILED)
        self.assertEqual(response.data['error_message'], 'Không tìm thấy lá trong ảnh.')
        self.assertIsNone(response.data['disease'])
        self.assertIsNone(response.data['recommendation'])

    @override_settings(DEBUG=False)
    def test_code_error_hides_details(self):
        # Giai đoạn chưa cài đặt: người dùng chỉ thấy thông báo chung
        with self.assertLogs('api.diagnosis', 'ERROR'):
            response, _ = self.post_image(side_effect=NotImplementedError('Thành viên 1: cài đặt resize()'))
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.FAILED)
        self.assertEqual(response.data['error_message'], diagnosis_service.SYSTEM_ERROR_MESSAGE)

    @override_settings(DEBUG=True)
    def test_code_error_details_in_debug(self):
        with self.assertLogs('api.diagnosis', 'ERROR'):
            response, _ = self.post_image(side_effect=NotImplementedError('Thành viên 1: cài đặt resize()'))
        self.assertIn('Thành viên 1: cài đặt resize()', response.data['error_message'])

    def test_unknown_disease_code_fails_without_partial_result(self):
        with self.assertLogs('api.diagnosis', 'ERROR'):
            response, _ = self.post_image(make_result(disease_code='Potato___Early_blight'))
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.FAILED)
        # DEBUG=False (mặc định khi test) vẫn có thông báo cụ thể, không phải câu chung
        self.assertEqual(
            response.data['error_message'],
            diagnosis_service.UNKNOWN_DISEASE_MESSAGE.format(code='Potato___Early_blight'),
        )
        self.assertIsNone(response.data['severity_level'])
        self.assertEqual(response.data['steps'], [])

    def post_image_failing_on_save(self):
        """Lỗi ở lần mã hóa ảnh thứ FAIL_ON_ENCODE: ảnh kết quả và vài ảnh bước trước đó đã được ghi xuống media."""
        real_encode = diagnosis_service.encode_image
        calls = []

        def flaky_encode(image):
            calls.append(1)
            if len(calls) == FAIL_ON_ENCODE:
                raise ValueError('lỗi giả')
            return real_encode(image)

        with mock.patch.object(diagnosis_service, 'encode_image', flaky_encode), self.assertLogs('api.diagnosis'):
            response, _ = self.post_image(make_result())
        self.assertEqual(len(calls), FAIL_ON_ENCODE)
        return response

    def test_steps_rolled_back_when_saving_fails(self):
        # Lỗi giữa chừng khi lưu ảnh từng bước -> không còn bước nào, không ở trạng thái done
        response = self.post_image_failing_on_save()
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.FAILED)
        self.assertFalse(DiagnosisStep.objects.exists())

    def test_no_leftover_files_when_saving_fails(self):
        # Thư mục media riêng để không lẫn file của các test khác
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media_root):
            response = self.post_image_failing_on_save()
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.FAILED)
        self.assertEqual(list_files(media_root, 'results'), [])
        self.assertEqual(list_files(media_root, 'steps'), [])
        # Ảnh gốc vẫn giữ để người dùng xem lại lần chẩn đoán lỗi
        self.assertEqual(len(list_files(media_root, 'uploads')), 1)

    def test_missing_image(self):
        response = self.client.post(URL, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)
        self.assertFalse(DiagnosisHistory.objects.exists())

    def test_not_an_image(self):
        upload = SimpleUploadedFile('la.png', b'khong phai anh', content_type='image/png')
        response = self.client.post(URL, {'image': upload}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gif_rejected(self):
        response = self.client.post(URL, {'image': make_upload('GIF', 'la.gif')}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('JPG hoặc PNG', str(response.data['image']))

    def test_too_large(self):
        with mock.patch('api.serializers.MAX_UPLOAD_BYTES', 10):
            response = self.client.post(URL, {'image': make_upload()}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(URL, {}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_401_UNAUTHORIZED)

    # ---------- GET / PATCH ----------

    def make_history(self, user=None, **fields):
        return DiagnosisHistory.objects.create(
            user=user or self.user, original_image='uploads/thu.jpg', **fields,
        )

    def test_list_only_own_newest_first(self):
        first = self.make_history()
        second = self.make_history()
        self.make_history(user=self.other)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual([item['id'] for item in response.data['results']], [second.pk, first.pk])
        self.assertIn('next', response.data)

    def test_retrieve(self):
        history = self.make_history()
        response = self.client.get(f'{URL}{history.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], DiagnosisHistory.Status.PENDING)

    def test_cannot_see_other_users_diagnosis(self):
        history = self.make_history(user=self.other)
        self.assertEqual(self.client.get(f'{URL}{history.pk}/').status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.patch(f'{URL}{history.pk}/', {'is_bookmarked': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bookmark(self):
        history = self.make_history()
        response = self.client.patch(f'{URL}{history.pk}/', {'is_bookmarked': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_bookmarked'])
        history.refresh_from_db()
        self.assertTrue(history.is_bookmarked)

    def test_patch_cannot_change_result(self):
        history = self.make_history()
        self.client.patch(
            f'{URL}{history.pk}/', {'status': 'done', 'severity_level': 4, 'infected_ratio': '0.9'}, format='json',
        )
        history.refresh_from_db()
        self.assertEqual(history.status, DiagnosisHistory.Status.PENDING)
        self.assertIsNone(history.severity_level)

    def test_put_and_delete_not_allowed(self):
        history = self.make_history()
        url = f'{URL}{history.pk}/'
        self.assertEqual(self.client.put(url, {}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(DiagnosisHistory.objects.filter(pk=history.pk).exists())


class ToDecimalTests(APITestCase):
    def test_rounds_to_4_places(self):
        self.assertEqual(diagnosis_service.to_decimal(0.87654), Decimal('0.8765'))
        self.assertEqual(diagnosis_service.to_decimal(1.0), Decimal('1.0000'))
