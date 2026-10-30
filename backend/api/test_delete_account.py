"""Test xóa tài khoản (POST /api/auth/delete-account/)."""
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from . import serializers
from .models import DiagnosisHistory, Feedback, User

URL = '/api/auth/delete-account/'
EMAIL = 'se.xoa@example.com'
PASSWORD = 'la-ca-chua-2026!'


class DeleteAccountTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            EMAIL, PASSWORD, fullname='Sẽ Xóa', terms_accepted_at=timezone.now(),
        )
        self.history = DiagnosisHistory.objects.create(user=self.user, original_image='uploads/la.png')
        self.feedback = Feedback.objects.create(history=self.history, title='Sai', description='Sai bệnh')
        self.tokens = self.login()

    def login(self, email=EMAIL, password=PASSWORD):
        return self.client.post('/api/auth/login/', {'email': email, 'password': password}, format='json')

    def auth(self, access):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def delete_account(self, password=PASSWORD):
        self.auth(self.tokens.data['access'])
        return self.client.post(URL, {'password': password}, format='json')

    def test_delete_anonymizes_user(self):
        response = self.delete_account()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

        self.user.refresh_from_db()
        self.assertIsNone(self.user.email)
        self.assertIsNone(self.user.username)
        self.assertEqual(self.user.fullname, 'Người dùng đã xóa')
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.has_usable_password())
        self.assertIsNotNone(self.user.deleted_at)
        # Không xóa cứng
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_history_kept_without_personal_info(self):
        self.delete_account()
        history = DiagnosisHistory.objects.select_related('user').get(pk=self.history.pk)
        self.assertEqual(history.user_id, self.user.pk)
        self.assertIsNone(history.user.email)
        self.assertNotIn('Sẽ Xóa', history.user.fullname)
        self.assertTrue(Feedback.objects.filter(pk=self.feedback.pk).exists())

    def test_cannot_login_after_delete(self):
        self.delete_account()
        self.client.credentials()
        self.assertEqual(self.login().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_old_tokens_revoked(self):
        other_device = self.login()  # đăng nhập trên thiết bị khác
        self.assertEqual(self.delete_account().status_code, status.HTTP_204_NO_CONTENT)

        # Access token cũ không gọi API được nữa
        self.auth(self.tokens.data['access'])
        self.assertEqual(self.client.get('/api/diagnoses/').status_code, status.HTTP_401_UNAUTHORIZED)

        # Mọi refresh token (cả thiết bị khác) đều bị thu hồi
        self.client.credentials()
        for tokens in (self.tokens, other_device):
            response = self.client.post('/api/auth/refresh/', {'refresh': tokens.data['refresh']}, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        outstanding = OutstandingToken.objects.filter(user=self.user)
        self.assertEqual(BlacklistedToken.objects.filter(token__in=outstanding).count(), outstanding.count())

    def test_email_can_register_again(self):
        self.delete_account()
        self.client.credentials()
        response = self.client.post('/api/auth/register/', {
            'email': EMAIL, 'fullname': 'Người Mới', 'password': PASSWORD, 'accept_terms': True,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Tài khoản mới không thấy lịch sử của tài khoản đã xóa
        self.auth(response.data['access'])
        listing = self.client.get('/api/diagnoses/')
        self.assertEqual(listing.data['count'], 0)
        self.assertEqual(self.client.get(f'/api/diagnoses/{self.history.pk}/').status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_password(self):
        response = self.delete_account(password='sai-mat-khau')
        # 400, không phải 401: frontend không được hiểu là hết phiên đăng nhập
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['password'], [serializers.WRONG_PASSWORD_MESSAGE])

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, EMAIL)
        self.assertTrue(self.user.is_active)
        self.assertFalse(BlacklistedToken.objects.exists())
        self.assertEqual(self.client.get('/api/diagnoses/').status_code, status.HTTP_200_OK)

    def test_staff_cannot_delete_self(self):
        for flags in ({'is_staff': True}, {'is_superuser': True}):
            with self.subTest(**flags):
                User.objects.filter(pk=self.user.pk).update(**{'is_staff': False, 'is_superuser': False, **flags})
                response = self.delete_account()
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data['non_field_errors'], [serializers.STAFF_SELF_DELETE_MESSAGE])

                self.user.refresh_from_db()
                self.assertEqual(self.user.email, EMAIL)
                self.assertTrue(self.user.is_active)
                self.assertFalse(BlacklistedToken.objects.exists())

    def test_staff_rejected_before_password_check(self):
        # Admin nhập sai mật khẩu vẫn nhận thông báo "xóa trong /admin/", không phải "sai mật khẩu"
        User.objects.filter(pk=self.user.pk).update(is_staff=True)
        response = self.delete_account(password='sai-mat-khau')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertNotIn('password', response.data)

    def test_password_not_trimmed(self):
        response = self.delete_account(password=f' {PASSWORD} ')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_password(self):
        self.auth(self.tokens.data['access'])
        response = self.client.post(URL, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_requires_login(self):
        response = self.client.post(URL, {'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_only_post(self):
        self.auth(self.tokens.data['access'])
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
