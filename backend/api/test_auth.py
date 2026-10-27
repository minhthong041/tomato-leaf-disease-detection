"""Test đăng ký tài khoản (POST /api/auth/register/)."""
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from . import serializers
from .models import User

URL = '/api/auth/register/'
STRONG_PASSWORD = 'la-ca-chua-2026!'


def register_data(**overrides):
    data = {
        'email': 'nguoi.moi@example.com',
        'fullname': 'Người Mới',
        'password': STRONG_PASSWORD,
        'accept_terms': True,
    }
    data.update(overrides)
    return data


class RegisterTests(APITestCase):
    def register(self, **overrides):
        return self.client.post(URL, register_data(**overrides), format='json')

    def test_register_success_logs_in(self):
        response = self.register(email='Nguoi.Moi@Example.com')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(set(response.data), {'access', 'refresh'})

        user = User.objects.get()
        self.assertEqual(user.email, 'nguoi.moi@example.com')  # lưu chữ thường
        self.assertEqual(user.fullname, 'Người Mới')
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertIsNotNone(user.terms_accepted_at)
        self.assertEqual(user.terms_version, settings.TERMS_VERSION)
        self.assertFalse(user.is_staff)
        self.assertNotIn('password', response.data)

        # Token trả về dùng được ngay: gọi API cần đăng nhập
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        self.assertEqual(self.client.get('/api/diagnoses/').status_code, status.HTTP_200_OK)

    def test_duplicate_email_ignores_case(self):
        User.objects.create_user(
            'da.co@example.com', STRONG_PASSWORD, fullname='Đã Có', terms_accepted_at=timezone.now(),
        )
        response = self.register(email='DA.CO@Example.COM')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['email'], [serializers.EMAIL_TAKEN_MESSAGE])
        self.assertEqual(User.objects.count(), 1)

    def test_terms_not_accepted(self):
        response = self.register(accept_terms=False)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['accept_terms'], [serializers.TERMS_REQUIRED_MESSAGE])
        self.assertFalse(User.objects.exists())

    def test_terms_missing(self):
        data = register_data()
        del data['accept_terms']
        response = self.client.post(URL, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('accept_terms', response.data)

    def test_weak_password(self):
        for password in ('12345678', 'abc', 'password'):
            with self.subTest(password=password):
                response = self.register(password=password)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('password', response.data)
        self.assertFalse(User.objects.exists())

    def test_password_too_similar_to_email(self):
        response = self.register(email='cachua.xanh@example.com', password='cachua.xanh')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_missing_fields(self):
        response = self.client.post(URL, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue({'email', 'fullname', 'password', 'accept_terms'} <= set(response.data))

    def test_anonymized_email_can_register_again(self):
        old = User.objects.create_user(
            'quay.lai@example.com', STRONG_PASSWORD, fullname='Cũ', terms_accepted_at=timezone.now(),
        )
        old.anonymize()
        response = self.register(email='quay.lai@example.com')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        new = User.objects.get(email='quay.lai@example.com')
        self.assertNotEqual(new.pk, old.pk)

    def test_ignores_stale_token(self):
        # Trình duyệt còn token cũ hỏng vẫn đăng ký được (view không đọc token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer token-cu-khong-hop-le')
        self.assertEqual(self.register().status_code, status.HTTP_201_CREATED)

    def test_cannot_set_admin_fields(self):
        response = self.register(is_staff=True, is_superuser=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get()
        self.assertFalse(user.is_staff or user.is_superuser)
