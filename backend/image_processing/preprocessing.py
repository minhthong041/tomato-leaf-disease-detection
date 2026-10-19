"""Giai đoạn 1 — Thu nhận và tiền xử lý ảnh. Phụ trách: Thành viên 1.

Mọi ảnh trong module là ảnh màu BGR (thứ tự kênh của OpenCV), kiểu uint8.
Quy ước vào/ra chung: docs/pipeline.md
"""
import numpy as np

from . import steps

# Tham số theo docs/TongQuanDuAn.md, hiệu chỉnh ở tuần 3
TARGET_SIZE = 512 # ảnh sau resize có kích thước TARGET_SIZE x TARGET_SIZE
BILATERAL_D = 9
BILATERAL_SIGMA_COLOR = 75
BILATERAL_SIGMA_SPACE = 75
MEDIAN_KSIZE = 5 # nếu dùng Median Blur thay cho Bilateral
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)


def resize(image: np.ndarray) -> np.ndarray:
    """Chuẩn hóa kích thước ảnh về (TARGET_SIZE, TARGET_SIZE, 3)."""
    raise NotImplementedError('Thành viên 1: cài đặt resize()')


def denoise(image: np.ndarray) -> np.ndarray:
    """Khử nhiễu bảo toàn cạnh: cv2.bilateralFilter (hoặc cv2.medianBlur). Giữ nguyên kích thước."""
    raise NotImplementedError('Thành viên 1: cài đặt denoise()')


def equalize(image: np.ndarray) -> np.ndarray:
    """Cân bằng sáng cục bộ: BGR -> LAB, CLAHE trên kênh L, LAB -> BGR. Giữ nguyên kích thước."""
    raise NotImplementedError('Thành viên 1: cài đặt equalize()')


def preprocess(image: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Chạy cả giai đoạn 1.

    Trả về (ảnh đã tiền xử lý, ảnh trung gian {RESIZED, DENOISED, CLAHE}).
    """
    resized = resize(image)
    denoised = denoise(resized)
    equalized = equalize(denoised)
    return equalized, {
        steps.RESIZED: resized,
        steps.DENOISED: denoised,
        steps.CLAHE: equalized,
    }
