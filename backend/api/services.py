"""Chạy pipeline xử lý ảnh cho một lần chẩn đoán và lưu kết quả vào database. Phụ trách: Thành viên 4.

Quy ước kết quả pipeline: docs/pipeline.md (mục 5).
"""
import json
import logging
from decimal import Decimal

import cv2
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from image_processing import pipeline

from .models import DiagnosisHistory, DiagnosisStep, Disease

logger = logging.getLogger(__name__)

# Thông báo cho người dùng khi lỗi do code (không phải do ảnh)
SYSTEM_ERROR_MESSAGE = 'Hệ thống chưa xử lý được ảnh này. Vui lòng thử lại sau.'
# Thông báo khi mô hình trả mã bệnh không có trong bảng diseases (nhãn model lệch với diseases.code)
UNKNOWN_DISEASE_MESSAGE = (
    'Mô hình trả về loại bệnh "{code}" không có trong danh sách bệnh của hệ thống. '
    'Vui lòng báo quản trị viên.'
)
# Ảnh kết quả và ảnh từng bước lưu dạng PNG để mask không bị nhiễu nén như JPG
RESULT_IMAGE_EXT = '.png'
# Số chữ số thập phân của cột decimal(5,4)
DECIMAL_PLACES = Decimal('0.0001')


class UnknownDiseaseError(Exception):
    """Mã bệnh pipeline trả về không có trong bảng diseases. Thông báo được hiện cho người dùng."""

    def __init__(self, code):
        self.code = code
        super().__init__(UNKNOWN_DISEASE_MESSAGE.format(code=code))


def decode_image(field_file) -> np.ndarray:
    """Đọc ảnh đã lưu (đã xóa EXIF, đã xoay đúng chiều) thành ảnh BGR uint8."""
    with field_file.open('rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
    if image is None:
        raise pipeline.PipelineError('Không đọc được ảnh. Hãy tải lên ảnh JPG hoặc PNG.')
    return image


def _to_png_file(image: np.ndarray) -> ContentFile:
    ok, buffer = cv2.imencode(RESULT_IMAGE_EXT, image)
    if not ok:
        raise ValueError(f'Không mã hóa được ảnh {image.dtype} {image.shape}')
    # Tên file chỉ để lấy đuôi; đường dẫn thật do upload_to tạo (uuid)
    return ContentFile(buffer.tobytes(), name=f'anh{RESULT_IMAGE_EXT}')


def to_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_PLACES)


def to_json(value):
    """Đổi kiểu numpy (np.int64, np.float64...) trong danh sách đốm bệnh sang kiểu Python để lưu JSONField."""
    return json.loads(json.dumps(value, default=lambda o: o.item() if hasattr(o, 'item') else o.tolist()))


def save_with_file(instance, field_file, saved_files: list) -> None:
    """instance.save() và ghi field_file vào saved_files nếu file đã được ghi xuống media.

    Django ghi file trước rồi mới ghi database, nên kể cả khi database lỗi file vẫn có thể đã nằm trên đĩa.
    Trước khi lưu, field_file.name là tên tạm; ghi file xong name đổi thành đường dẫn thật (uuid).
    """
    temp_name = field_file.name
    try:
        instance.save()
    finally:
        if field_file.name != temp_name:
            saved_files.append(field_file)


def delete_files(saved_files: list) -> None:
    """Xóa các file ảnh đã ghi khi lưu kết quả thất bại (database đã rollback nên không còn dòng nào trỏ tới)."""
    for field_file in saved_files:
        try:
            field_file.delete(save=False)
        except OSError:
            # Không để lỗi xóa file che mất lỗi gốc
            logger.warning('Không xóa được file %s', field_file.name, exc_info=True)


def save_result(history: DiagnosisHistory, result: pipeline.PipelineResult) -> None:
    disease = Disease.objects.filter(code=result.disease_code).first()
    if disease is None:
        # Kiểm tra trước transaction -> chưa ghi file hay dòng nào vào database
        raise UnknownDiseaseError(result.disease_code)

    # File đã ghi vào media/results, media/steps -> xóa nếu lưu thất bại giữa chừng
    saved_files = []
    try:
        with transaction.atomic():
            history.status = DiagnosisHistory.Status.DONE
            history.error_message = None
            history.disease = disease
            history.disease_confidence = to_decimal(result.disease_confidence)
            history.severity_level = result.severity_level
            history.leaf_area_px = result.leaf_area_px
            history.lesion_area_px = result.lesion_area_px
            history.infected_ratio = to_decimal(result.infected_ratio)
            history.lesion_count = result.lesion_count
            history.lesions = to_json(result.lesions)
            history.processed_image = _to_png_file(result.processed_image)
            save_with_file(history, history.processed_image, saved_files)
            # Lưu theo đúng thứ tự steps.ORDER -> history.steps.all() (sắp theo id) đúng thứ tự hiển thị
            for name, image in result.steps.items():
                step = DiagnosisStep(history=history, step=name, image=_to_png_file(image))
                save_with_file(step, step.image, saved_files)
    except Exception:
        delete_files(saved_files)
        raise


def mark_failed(history: DiagnosisHistory, message: str) -> None:
    # Bỏ các trường kết quả đã gán dở trong bộ nhớ (database đã rollback)
    history.refresh_from_db()
    history.status = DiagnosisHistory.Status.FAILED
    history.error_message = message
    history.save(update_fields=['status', 'error_message', 'updated_at'])


def run_diagnosis(history: DiagnosisHistory) -> DiagnosisHistory:
    """Chạy pipeline trên ảnh gốc của history. Luôn kết thúc ở trạng thái done hoặc failed."""
    history.status = DiagnosisHistory.Status.PROCESSING
    history.save(update_fields=['status', 'updated_at'])
    try:
        result = pipeline.run(decode_image(history.original_image))
        save_result(history, result)
    except pipeline.PipelineError as error:
        # Lỗi do ảnh: báo nguyên văn cho người dùng
        mark_failed(history, str(error))
    except UnknownDiseaseError as error:
        # Lỗi cấu hình (nhãn model lệch bảng diseases): ghi log cho nhóm, báo rõ cho người dùng
        logger.error('Chẩn đoán #%s: mã bệnh %r không có trong bảng diseases', history.pk, error.code)
        mark_failed(history, str(error))
    except Exception as error:
        # Lỗi do code (NotImplementedError, ValueError sai quy ước...): ghi log đầy đủ
        logger.exception('Chẩn đoán #%s lỗi', history.pk)
        message = SYSTEM_ERROR_MESSAGE
        if settings.DEBUG:
            # Lúc phát triển hiện luôn lỗi để biết giai đoạn nào chưa xong
            message += f' ({type(error).__name__}: {error})'
        mark_failed(history, message)
    return history
