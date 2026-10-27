from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image
from rest_framework import serializers

from image_processing.severity import IPM_RECOMMENDATIONS

from .models import DiagnosisHistory, DiagnosisStep, Disease, User

# Ảnh tải lên: chỉ nhận JPG/PNG, tối đa MAX_UPLOAD_MB
ALLOWED_IMAGE_FORMATS = ('JPEG', 'PNG')
MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Đăng ký tài khoản
FULLNAME_MAX_LENGTH = 255  # trùng users.fullname
EMAIL_TAKEN_MESSAGE = 'Email này đã được dùng để đăng ký.'
TERMS_REQUIRED_MESSAGE = 'Bạn cần đồng ý điều khoản sử dụng để đăng ký.'


class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = ('code', 'name', 'is_healthy')


class DiagnosisStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisStep
        fields = ('step', 'image')


class DiagnosisSerializer(serializers.ModelSerializer):
    """Một lần chẩn đoán, đúng cấu trúc frontend/src/api/diagnoses.js. Chỉ sửa được is_bookmarked."""

    disease = DiseaseSerializer(read_only=True)
    steps = DiagnosisStepSerializer(many=True, read_only=True)
    recommendation = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosisHistory
        fields = (
            'id', 'status', 'error_message',
            'original_image', 'processed_image',
            'disease', 'disease_confidence',
            'severity_level', 'recommendation',
            'infected_ratio', 'leaf_area_px', 'lesion_area_px', 'lesion_count', 'lesions',
            'steps', 'is_bookmarked', 'created_at',
        )
        read_only_fields = tuple(name for name in fields if name != 'is_bookmarked')

    def get_recommendation(self, obj):
        if obj.severity_level is None:
            return None
        return IPM_RECOMMENDATIONS[obj.severity_level]


class DiagnosisCreateSerializer(serializers.Serializer):
    """Dữ liệu gửi lên khi tạo chẩn đoán: multipart, trường "image"."""

    image = serializers.ImageField()

    def validate_image(self, file):
        if file.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError(f'Ảnh vượt quá {MAX_UPLOAD_MB} MB.')
        # ImageField đã kiểm tra là ảnh hợp lệ; ở đây kiểm tra định dạng thật, không tin đuôi file
        file.seek(0)
        with Image.open(file) as img:
            image_format = img.format
        file.seek(0)
        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise serializers.ValidationError('Chỉ nhận ảnh JPG hoặc PNG.')
        return file


class RegisterSerializer(serializers.Serializer):
    """Dữ liệu đăng ký: email, fullname, password, accept_terms (bắt buộc true)."""

    email = serializers.EmailField(max_length=255)
    fullname = serializers.CharField(max_length=FULLNAME_MAX_LENGTH)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    accept_terms = serializers.BooleanField()

    def validate_email(self, value):
        email = value.strip().lower()
        # Không phân biệt hoa thường; tài khoản đã ẩn danh hóa có email NULL nên không bị tính
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(EMAIL_TAKEN_MESSAGE)
        return email

    def validate_accept_terms(self, value):
        if value is not True:
            raise serializers.ValidationError(TERMS_REQUIRED_MESSAGE)
        return value

    def validate(self, attrs):
        # User tạm (chưa lưu) để UserAttributeSimilarityValidator so mật khẩu với email, họ tên
        candidate = User(email=attrs['email'], fullname=attrs['fullname'])
        try:
            validate_password(attrs['password'], user=candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)})
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=validated_data['email'],
                    password=validated_data['password'],
                    fullname=validated_data['fullname'],
                    terms_accepted_at=timezone.now(),
                )
        except IntegrityError:
            # Hai yêu cầu đăng ký cùng email gần như đồng thời: ràng buộc unique của database chặn lại
            raise serializers.ValidationError({'email': [EMAIL_TAKEN_MESSAGE]})
