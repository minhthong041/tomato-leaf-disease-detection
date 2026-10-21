from PIL import Image
from rest_framework import serializers

from image_processing.severity import IPM_RECOMMENDATIONS

from .models import DiagnosisHistory, DiagnosisStep, Disease

# Ảnh tải lên: chỉ nhận JPG/PNG, tối đa MAX_UPLOAD_MB
ALLOWED_IMAGE_FORMATS = ('JPEG', 'PNG')
MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


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
