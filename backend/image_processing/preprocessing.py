"""Giai đoạn 1 — Thu nhận và tiền xử lý ảnh. Phụ trách: Thành viên 1.

Mọi ảnh trong module là ảnh màu BGR (thứ tự kênh của OpenCV), kiểu uint8.
Quy ước vào/ra chung: docs/pipeline.md
"""
import cv2
import numpy as np

from . import steps

# Tham số theo docs/TongQuanDuAn.md, hiệu chỉnh ở tuần 3
TARGET_SIZE = 512 # ảnh sau resize có kích thước TARGET_SIZE x TARGET_SIZE
# Thu nhỏ (ảnh tự chụp) dùng INTER_AREA để không răng cưa; phóng to (PlantVillage 256x256) dùng INTER_CUBIC
SHRINK_INTERPOLATION = cv2.INTER_AREA
ENLARGE_INTERPOLATION = cv2.INTER_CUBIC
BILATERAL_D = 9
BILATERAL_SIGMA_COLOR = 75
BILATERAL_SIGMA_SPACE = 75
MEDIAN_KSIZE = 5 # nếu dùng Median Blur thay cho Bilateral
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)


def resize(image: np.ndarray) -> np.ndarray:
    """Chuẩn hóa kích thước ảnh về (TARGET_SIZE, TARGET_SIZE, 3).

    Ảnh không vuông bị kéo giãn thẳng về hình vuông, không thêm viền: viền màu sẽ làm sai bước tách lá.
    Lá và vết bệnh giãn cùng tỉ lệ nên S% không đổi, chỉ circularity của từng đốm bị méo nhẹ.
    Chỉ dùng INTER_AREA khi cả hai chiều đều thu nhỏ (phóng to bằng INTER_AREA gần như nearest).
    """
    height, width = image.shape[:2]
    shrinking = height >= TARGET_SIZE and width >= TARGET_SIZE
    interpolation = SHRINK_INTERPOLATION if shrinking else ENLARGE_INTERPOLATION
    return cv2.resize(image, (TARGET_SIZE, TARGET_SIZE), interpolation=interpolation)


def denoise(image: np.ndarray) -> np.ndarray:
    """Khử nhiễu bảo toàn cạnh bằng cv2.bilateralFilter. Giữ nguyên kích thước."""
    return cv2.bilateralFilter(image, BILATERAL_D, BILATERAL_SIGMA_COLOR, BILATERAL_SIGMA_SPACE)


def equalize(image: np.ndarray) -> np.ndarray:
    """Cân bằng sáng cục bộ: BGR -> LAB, CLAHE trên kênh L, LAB -> BGR. Giữ nguyên kích thước.

    Chỉ đổi kênh L (độ sáng), giữ nguyên A, B nên màu lá và vết bệnh không bị lệch.
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID)
    lab = cv2.merge((clahe.apply(lightness), a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


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
