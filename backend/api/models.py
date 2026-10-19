from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone

from .images import (
    diagnosis_original_path, diagnosis_processed_path, diagnosis_step_path, strip_image_metadata,
)

# Schema: docs/leaf-disease-db.md — mô tả chi tiết: docs/database.md


# ==========================================
# 1. MODEL DÙNG CHUNG
# ==========================================

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ==========================================
# 2. NGƯỜI DÙNG (CUSTOM USER MODEL)
# ==========================================

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email là bắt buộc')
        if not extra_fields.get('terms_accepted_at'):
            raise ValueError('Người dùng phải đồng ý điều khoản sử dụng (terms_accepted_at)')
        extra_fields.setdefault('terms_version', settings.TERMS_VERSION)
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password) # Băm vào cột password_hash
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # Tài khoản quản trị tạo bằng lệnh createsuperuser, không qua màn hình đăng ký
        extra_fields.setdefault('terms_accepted_at', timezone.now())
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        # Đăng nhập không phân biệt hoa thường
        return self.get(email__iexact=email)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    # unique=True giữ lại vì Django yêu cầu USERNAME_FIELD unique; unique không phân biệt
    # hoa thường nằm ở Meta.constraints. NULL khi tài khoản đã bị xóa (ẩn danh hóa).
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)
    fullname = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    password = models.CharField(max_length=255, db_column='password_hash')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    terms_accepted_at = models.DateTimeField()
    terms_version = models.CharField(max_length=20)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['fullname']

    class Meta:
        db_table = 'users'
        verbose_name = 'người dùng'
        verbose_name_plural = 'người dùng'
        constraints = [
            models.CheckConstraint(
                condition=Q(deleted_at__isnull=False) | Q(email__isnull=False),
                name='users_active_requires_email',
            ),
            models.UniqueConstraint(Lower('email'), name='users_email_ci_unique'),
            models.UniqueConstraint(Lower('username'), name='users_username_ci_unique'),
        ]

    def __str__(self):
        return self.email or f'[Đã xóa #{self.pk}]'

    def save(self, *args, **kwargs):
        # Form để trống sẽ gửi '' — đổi thành NULL để không vướng ràng buộc unique
        self.username = self.username or None
        self.email = self.email or None
        super().save(*args, **kwargs)

    def anonymize(self):
        """Xóa tài khoản: xóa thông tin cá nhân nhưng giữ dòng để lịch sử chẩn đoán còn nguyên."""
        self.email = None
        self.username = None
        self.fullname = 'Người dùng đã xóa'
        self.set_unusable_password()
        self.is_active = False
        self.is_staff = False
        self.is_superuser = False
        self.deleted_at = timezone.now()
        self.save()
        self.groups.clear()
        self.user_permissions.clear()


# ==========================================
# 3. DANH MỤC BỆNH (LỚP CỦA BỘ PHÂN LOẠI)
# ==========================================

class Disease(TimeStampedModel):
    # Mỗi dòng là một lớp bệnh lá cà chua của bộ phân loại (nhãn PlantVillage), kể cả lớp lá khỏe
    code = models.CharField(max_length=100, unique=True) # ví dụ Tomato___Early_blight
    name = models.CharField(max_length=255) # tên tiếng Việt hiển thị cho người dùng
    description = models.TextField(null=True, blank=True)
    is_healthy = models.BooleanField(default=False) # lớp Tomato___healthy

    class Meta:
        db_table = 'diseases'
        ordering = ['name']
        verbose_name = 'bệnh'
        verbose_name_plural = 'bệnh'
        constraints = [
            # Chỉ có một lớp "lá khỏe"
            models.UniqueConstraint(
                fields=['is_healthy'], condition=Q(is_healthy=True), name='diseases_one_healthy',
            ),
        ]

    def __str__(self):
        return self.name


# ==========================================
# 4. NGHIỆP VỤ (LỊCH SỬ, FEEDBACK, BÁO LỖI)
# ==========================================

class DiagnosisHistory(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ xử lý'
        PROCESSING = 'processing', 'Đang xử lý'
        DONE = 'done', 'Hoàn tất'
        FAILED = 'failed', 'Lỗi'

    # Thang Cấp 0–4 theo tỷ lệ diện tích bệnh S = lesion_area_px / leaf_area_px
    class SeverityLevel(models.IntegerChoices):
        HEALTHY = 0, 'Cấp 0 - Khỏe mạnh' # S = 0%
        MILD = 1, 'Cấp 1 - Nhiễm nhẹ' # 0% < S < 5%
        MODERATE = 2, 'Cấp 2 - Trung bình' # 5% <= S < 15%
        SEVERE = 3, 'Cấp 3 - Nặng' # 15% <= S <= 35%
        CRITICAL = 4, 'Cấp 4 - Nguy kịch' # S > 35%

    # PROTECT: tài khoản chỉ được ẩn danh hóa, không xóa thật -> giữ lịch sử chẩn đoán
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='diagnoses', db_index=False, # đã có idx_dh_user_created
    )
    original_image = models.ImageField(upload_to=diagnosis_original_path, max_length=500)
    # Ảnh gốc đã vẽ đường viền (contours) quanh các vết bệnh
    processed_image = models.ImageField(
        upload_to=diagnosis_processed_path, max_length=500, null=True, blank=True,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True,
    )
    error_message = models.TextField(null=True, blank=True)

    # Kết quả pipeline — NULL khi chưa có kết quả (pending/processing/failed)
    # Phân loại tên bệnh (giai đoạn 4)
    disease = models.ForeignKey(
        Disease, on_delete=models.PROTECT, null=True, blank=True, related_name='diagnoses',
    )
    disease_confidence = models.DecimalField( # xác suất của lớp dự đoán (predict_proba)
        max_digits=5, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    # Định lượng mức độ (giai đoạn 2, 3, 5)
    severity_level = models.PositiveSmallIntegerField(
        choices=SeverityLevel.choices, null=True, blank=True, db_index=True,
    )
    leaf_area_px = models.PositiveIntegerField(null=True, blank=True) # mask lá sau tách nền
    lesion_area_px = models.PositiveIntegerField(null=True, blank=True) # mask vết bệnh
    infected_ratio = models.DecimalField( # lesion_area_px / leaf_area_px
        max_digits=5, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    lesion_count = models.PositiveIntegerField(null=True, blank=True)
    # Mỗi đốm: {"area", "perimeter", "circularity", "center": [x, y], "bbox": [x, y, w, h]}
    lesions = models.JSONField(null=True, blank=True)

    is_bookmarked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True) # không index riêng, xem Meta.indexes

    class Meta:
        db_table = 'diagnosis_histories'
        ordering = ['-created_at']
        verbose_name = 'lịch sử chẩn đoán'
        verbose_name_plural = 'lịch sử chẩn đoán'
        indexes = [
            models.Index(fields=['user', 'created_at'], name='idx_dh_user_created'),
            models.Index(fields=['user', 'is_bookmarked'], name='idx_dh_user_bookmarked'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(infected_ratio__isnull=True)
                | Q(infected_ratio__gte=0, infected_ratio__lte=1),
                name='dh_ratio_between_0_1',
            ),
            models.CheckConstraint(
                condition=Q(lesion_area_px__isnull=True) | Q(leaf_area_px__isnull=True)
                | Q(lesion_area_px__lte=F('leaf_area_px')),
                name='dh_lesion_within_leaf',
            ),
            models.CheckConstraint(
                condition=Q(disease_confidence__isnull=True)
                | Q(disease_confidence__gte=0, disease_confidence__lte=1),
                name='dh_confidence_between_0_1',
            ),
            models.CheckConstraint(
                condition=Q(severity_level__isnull=True) | Q(severity_level__lte=4),
                name='dh_level_between_0_4',
            ),
            # Cấp 0 <=> không có vết bệnh. So trên lesion_area_px, không so trên infected_ratio
            # vì ratio làm tròn 4 chữ số có thể ra 0.0000 khi vẫn còn vết bệnh rất nhỏ
            models.CheckConstraint(
                condition=Q(severity_level__isnull=True) | Q(lesion_area_px__isnull=True)
                | Q(severity_level=0, lesion_area_px=0)
                | Q(severity_level__gt=0, lesion_area_px__gt=0),
                name='dh_level0_iff_no_lesion',
            ),
            models.CheckConstraint(
                condition=~Q(status='done') | Q(
                    disease__isnull=False, disease_confidence__isnull=False,
                    severity_level__isnull=False, leaf_area_px__isnull=False,
                    lesion_area_px__isnull=False, infected_ratio__isnull=False,
                    lesion_count__isnull=False,
                ),
                name='dh_done_requires_result',
            ),
        ]

    def __str__(self):
        return f'#{self.pk} - {self.get_status_display()}'

    def save(self, *args, **kwargs):
        # Ảnh mới tải lên: xóa EXIF (GPS, thiết bị) trước khi lưu
        if self.original_image and not self.original_image._committed:
            self.original_image = strip_image_metadata(self.original_image)
        super().save(*args, **kwargs)


class DiagnosisStep(TimeStampedModel):
    """Ảnh trung gian của một bước pipeline, để giao diện hiển thị chuỗi biến đổi."""

    class Step(models.TextChoices):
        # Giai đoạn 1: tiền xử lý
        RESIZED = 'resized', 'Chuẩn hóa kích thước'
        DENOISED = 'denoised', 'Khử nhiễu'
        CLAHE = 'clahe', 'Cân bằng sáng CLAHE'
        # Giai đoạn 2: tách phiến lá khỏi nền
        SATURATION = 'saturation', 'Kênh S (HSV)'
        LEAF_MASK = 'leaf_mask', 'Mặt nạ lá'
        # Giai đoạn 3: tách đốm bệnh
        ROI = 'roi', 'Vùng lá (ROI)'
        HEALTHY_MASK = 'healthy_mask', 'Mặt nạ mô lá khỏe'
        LESION_MASK_RAW = 'lesion_mask_raw', 'Mặt nạ vết bệnh (trước hình thái học)'
        LESION_MASK = 'lesion_mask', 'Mặt nạ vết bệnh (sau opening/closing)'
        # Ảnh contours cuối cùng nằm ở DiagnosisHistory.processed_image

    history = models.ForeignKey(
        DiagnosisHistory, on_delete=models.CASCADE,
        related_name='steps', db_index=False, # đã có uq_ds_history_step
    )
    step = models.CharField(max_length=30, choices=Step.choices)
    image = models.ImageField(upload_to=diagnosis_step_path, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True) # không cần index riêng

    class Meta:
        db_table = 'diagnosis_steps'
        ordering = ['id'] # pipeline lưu theo đúng thứ tự các bước
        verbose_name = 'ảnh bước xử lý'
        verbose_name_plural = 'ảnh bước xử lý'
        constraints = [
            models.UniqueConstraint(fields=['history', 'step'], name='uq_ds_history_step'),
        ]

    def __str__(self):
        return f'#{self.history_id} - {self.get_step_display()}'


class Feedback(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ duyệt'
        ACCEPTED = 'accepted', 'Chấp nhận'
        REJECTED = 'rejected', 'Từ chối'

    history = models.ForeignKey(DiagnosisHistory, on_delete=models.CASCADE, related_name='feedbacks')
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True,
    )

    class Meta:
        db_table = 'feedbacks'
        ordering = ['-created_at']
        verbose_name = 'phản hồi'
        verbose_name_plural = 'phản hồi'

    def __str__(self):
        return self.title


class ErrorReport(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='error_reports')
    title = models.CharField(max_length=255)
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)

    class Meta:
        db_table = 'error_reports'
        ordering = ['-created_at']
        verbose_name = 'báo lỗi'
        verbose_name_plural = 'báo lỗi'
        indexes = [
            # Partial index: chỉ chứa báo lỗi chưa xử lý (danh sách admin cần xem)
            models.Index(
                fields=['created_at'], condition=Q(is_resolved=False), name='idx_er_unresolved',
            ),
        ]

    def __str__(self):
        return self.title
