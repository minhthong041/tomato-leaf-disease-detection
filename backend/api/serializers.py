from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from image_processing.severity import IPM_RECOMMENDATIONS

from .models import DiagnosisHistory, DiagnosisStep, Disease, ErrorReport, Feedback, User
from .recommendations import disease_recommendation

# Ảnh tải lên: chỉ nhận JPG/PNG, tối đa MAX_UPLOAD_MB
ALLOWED_IMAGE_FORMATS = ('JPEG', 'PNG')
MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Đăng ký tài khoản
FULLNAME_MAX_LENGTH = 255  # trùng users.fullname
EMAIL_TAKEN_MESSAGE = 'Email này đã được dùng để đăng ký.'
TERMS_REQUIRED_MESSAGE = 'Bạn cần đồng ý điều khoản sử dụng để đăng ký.'

# Xóa tài khoản
WRONG_PASSWORD_MESSAGE = 'Mật khẩu không đúng.'
# Admin tự xóa sẽ mất quyền vào /admin/ (có thể không còn ai quản trị): chỉ xóa trong /admin/
STAFF_SELF_DELETE_MESSAGE = (
    'Tài khoản quản trị không tự xóa ở đây được. '
    'Hãy nhờ một quản trị viên khác xóa trong trang quản trị /admin/.'
)

# Phản hồi kết quả sai, báo lỗi
REPORT_DESCRIPTION_MAX_LENGTH = 5000  # đủ cho một mô tả, chặn gửi văn bản quá dài
HISTORY_NOT_FOUND_MESSAGE = 'Không tìm thấy lần chẩn đoán này.'
# Lần chẩn đoán chưa có kết quả (pending/processing) hoặc lỗi (failed) thì dùng trang Báo lỗi
HISTORY_NOT_DONE_MESSAGE = 'Chỉ gửi phản hồi được cho lần chẩn đoán đã có kết quả.'


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
    # Khuyến nghị theo bệnh (api/recommendations.py); recommendation ở trên là khuyến nghị theo cấp
    disease_recommendation = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosisHistory
        fields = (
            'id', 'status', 'error_message',
            'original_image', 'processed_image',
            'disease', 'disease_confidence',
            'severity_level', 'recommendation', 'disease_recommendation',
            'infected_ratio', 'leaf_area_px', 'lesion_area_px', 'lesion_count', 'lesions',
            'steps', 'is_bookmarked', 'created_at',
        )
        read_only_fields = tuple(name for name in fields if name != 'is_bookmarked')

    def get_recommendation(self, obj):
        if obj.severity_level is None:
            return None
        return IPM_RECOMMENDATIONS[obj.severity_level]

    def get_disease_recommendation(self, obj):
        if obj.disease is None:
            return None
        return disease_recommendation(obj.disease.code)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Trang Lịch sử không dùng khuyến nghị theo bệnh: bỏ khỏi API danh sách cho nhẹ
        view = self.context.get('view')
        if getattr(view, 'action', None) == 'list':
            data.pop('disease_recommendation', None)
        return data


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


class DeleteAccountSerializer(serializers.Serializer):
    """Xác nhận xóa tài khoản: nhập lại mật khẩu của tài khoản đang đăng nhập.

    Tài khoản quản trị (is_staff/is_superuser) bị từ chối trước khi kiểm tra mật khẩu.
    """

    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context['request'].user
        if user.is_staff or user.is_superuser:
            raise serializers.ValidationError(STAFF_SELF_DELETE_MESSAGE)
        if not user.check_password(attrs['password']):
            raise serializers.ValidationError({'password': [WRONG_PASSWORD_MESSAGE]})
        return attrs


class OwnDiagnosisField(serializers.PrimaryKeyRelatedField):
    """Mã lần chẩn đoán của chính người đang đăng nhập.

    Mã không tồn tại hoặc thuộc người khác đều trả 404 (giống GET /api/diagnoses/:id/),
    để không lộ việc bản ghi của người khác có tồn tại hay không.
    """

    def get_queryset(self):
        return DiagnosisHistory.objects.filter(user=self.context['request'].user)

    def to_internal_value(self, data):
        # bool là con của int (True == 1), float bị Django làm tròn (1.5 -> 1): đều không phải mã hợp lệ
        if isinstance(data, (bool, float)):
            self.fail('incorrect_type', data_type=type(data).__name__)
        try:
            return self.get_queryset().get(pk=data)
        except (TypeError, ValueError, DjangoValidationError):
            self.fail('incorrect_type', data_type=type(data).__name__)
        except DiagnosisHistory.DoesNotExist:
            # NotFound không phải ValidationError nên is_valid() để nó đi thẳng ra thành 404
            raise NotFound(HISTORY_NOT_FOUND_MESSAGE)


class FeedbackSerializer(serializers.ModelSerializer):
    """POST /api/feedbacks/ {history, title, description}: báo một kết quả chẩn đoán bị sai."""

    history = OwnDiagnosisField()
    description = serializers.CharField(max_length=REPORT_DESCRIPTION_MAX_LENGTH)

    class Meta:
        model = Feedback
        fields = ('id', 'history', 'title', 'description', 'status', 'created_at')
        read_only_fields = ('status', 'created_at')

    def validate_history(self, history):
        # Chạy sau OwnDiagnosisField: bản ghi của người khác đã trả 404 trước khi tới đây
        if history.status != DiagnosisHistory.Status.DONE:
            raise serializers.ValidationError(HISTORY_NOT_DONE_MESSAGE)
        return history


class ErrorReportSerializer(serializers.ModelSerializer):
    """POST /api/error-reports/ {title, description}: báo lỗi ứng dụng. Người gửi lấy từ tài khoản đăng nhập."""

    description = serializers.CharField(max_length=REPORT_DESCRIPTION_MAX_LENGTH)

    class Meta:
        model = ErrorReport
        fields = ('id', 'title', 'description', 'is_resolved', 'created_at')
        read_only_fields = ('is_resolved', 'created_at')
