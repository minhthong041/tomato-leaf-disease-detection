"""Test phản hồi kết quả sai (POST /api/feedbacks/) và báo lỗi (POST /api/error-reports/)."""
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from . import serializers
from .models import DiagnosisHistory, Disease, ErrorReport, Feedback, User

FEEDBACK_URL = '/api/feedbacks/'
ERROR_REPORT_URL = '/api/error-reports/'


def make_user(email, **extra):
    return User.objects.create_user(
        email, 'mat-khau-thu', fullname=email.split('@')[0], terms_accepted_at=timezone.now(), **extra,
    )


def make_history(user, status=DiagnosisHistory.Status.DONE):
    """Lần chẩn đoán của user. Trạng thái done cần đủ cột kết quả (CHECK constraint dh_done_requires_result)."""
    # Gán đường dẫn có sẵn -> không đọc file ảnh
    fields = {'user': user, 'original_image': 'uploads/thu.jpg', 'status': status}
    if status == DiagnosisHistory.Status.DONE:
        fields.update(
            disease=Disease.objects.get(code='Tomato___Early_blight'),
            disease_confidence=Decimal('0.9100'),
            severity_level=DiagnosisHistory.SeverityLevel.MODERATE,
            leaf_area_px=10000,
            lesion_area_px=850,
            infected_ratio=Decimal('0.0850'),
            lesion_count=3,
        )
    return DiagnosisHistory.objects.create(**fields)


class ReportTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user('tv4@example.com')
        cls.other = make_user('khac@example.com')
        cls.history = make_history(cls.user)
        cls.other_history = make_history(cls.other)

    def setUp(self):
        self.client.force_authenticate(self.user)


class FeedbackTests(ReportTestCase):
    def post(self, **overrides):
        data = {'history': self.history.pk, 'title': 'Kết quả sai', 'description': 'Lá khỏe nhưng bị cấp 3.'}
        data.update(overrides)
        return self.client.post(FEEDBACK_URL, data, format='json')

    def test_create(self):
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        feedback = Feedback.objects.get()
        self.assertEqual(feedback.history, self.history)
        self.assertEqual(feedback.status, Feedback.Status.PENDING)
        self.assertEqual(response.data['history'], self.history.pk)
        self.assertEqual(response.data['status'], Feedback.Status.PENDING)

    def test_other_users_history_returns_404(self):
        response = self.post(history=self.other_history.pk)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], serializers.HISTORY_NOT_FOUND_MESSAGE)
        self.assertFalse(Feedback.objects.exists())

    def test_unknown_history_returns_404(self):
        # Không phân biệt "không tồn tại" và "của người khác" -> không lộ bản ghi người khác
        response = self.post(history=999999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_title_returns_400(self):
        for title in (None, '', '   '):
            with self.subTest(title=title):
                data = {'history': self.history.pk, 'description': 'Mô tả'}
                if title is not None:
                    data['title'] = title
                response = self.client.post(FEEDBACK_URL, data, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('title', response.data)
        self.assertFalse(Feedback.objects.exists())

    def test_missing_description_and_history_return_400(self):
        response = self.client.post(FEEDBACK_URL, {'title': 'Sai'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue({'history', 'description'} <= set(response.data))

    def test_history_without_result_returns_400(self):
        # Chưa có kết quả hoặc lỗi: không "báo kết quả sai" được, dùng trang Báo lỗi
        Status = DiagnosisHistory.Status
        for status_value in (Status.PENDING, Status.PROCESSING, Status.FAILED):
            with self.subTest(status=status_value):
                history = make_history(self.user, status=status_value)
                response = self.post(history=history.pk)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data['history'], [serializers.HISTORY_NOT_DONE_MESSAGE])
        self.assertFalse(Feedback.objects.exists())

    def test_other_users_unfinished_history_still_404(self):
        # Không lộ trạng thái bản ghi của người khác: vẫn 404, không phải 400
        history = make_history(self.other, status=DiagnosisHistory.Status.FAILED)
        self.assertEqual(self.post(history=history.pk).status_code, status.HTTP_404_NOT_FOUND)

    def test_history_wrong_type_returns_400(self):
        # 1.5 không được làm tròn thành bản ghi id 1
        for value in ('abc', True, [1], 1.5, float(self.history.pk), '1.5'):
            with self.subTest(value=value):
                self.assertEqual(self.post(history=value).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Feedback.objects.exists())

    def test_too_long_description_returns_400(self):
        response = self.post(description='a' * (serializers.REPORT_DESCRIPTION_MAX_LENGTH + 1))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_set_status(self):
        self.post(status=Feedback.Status.ACCEPTED)
        self.assertEqual(Feedback.objects.get().status, Feedback.Status.PENDING)

    def test_login_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.post().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_only_post(self):
        self.assertEqual(self.client.get(FEEDBACK_URL).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ErrorReportTests(ReportTestCase):
    def post(self, **overrides):
        data = {'title': 'Không tải được ảnh', 'description': 'Bấm Chẩn đoán thì trang đứng yên.'}
        data.update(overrides)
        return self.client.post(ERROR_REPORT_URL, data, format='json')

    def test_create(self):
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        report = ErrorReport.objects.get()
        self.assertEqual(report.user, self.user)
        self.assertFalse(report.is_resolved)
        self.assertNotIn('user', response.data)

    def test_user_comes_from_login_not_request_body(self):
        response = self.post(user=self.other.pk, is_resolved=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report = ErrorReport.objects.get()
        self.assertEqual(report.user, self.user)
        self.assertFalse(report.is_resolved)

    def test_missing_title_returns_400(self):
        response = self.client.post(ERROR_REPORT_URL, {'description': 'Mô tả'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        self.assertFalse(ErrorReport.objects.exists())

    def test_missing_description_returns_400(self):
        response = self.post(description='')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('description', response.data)

    def test_login_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.post().status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(ErrorReport.objects.exists())


class AdminListTests(ReportTestCase):
    """Phản hồi và báo lỗi gửi lên hiện trong /admin/ để quản trị viên xử lý."""

    def test_admin_sees_feedback_and_error_report(self):
        self.client.post(
            FEEDBACK_URL, {'history': self.history.pk, 'title': 'Phản hồi thử', 'description': 'x'}, format='json',
        )
        self.client.post(ERROR_REPORT_URL, {'title': 'Báo lỗi thử', 'description': 'y'}, format='json')

        admin = User.objects.create_superuser('admin@example.com', 'mat-khau-thu', fullname='Quản trị')
        self.client.force_login(admin)
        self.assertContains(self.client.get('/admin/api/feedback/'), 'Phản hồi thử')
        self.assertContains(self.client.get('/admin/api/errorreport/'), 'Báo lỗi thử')
