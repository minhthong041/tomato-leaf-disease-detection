"""Giai đoạn 2 và 3 — Tách phiến lá khỏi nền, tách đốm bệnh, đo từng đốm. Phụ trách: Thành viên 2.

Mask là ảnh xám uint8 cùng kích thước với ảnh vào, chỉ gồm 0 (nền) và 255 (vùng được chọn).
Kênh H của HSV trong OpenCV chạy 0–179, không phải 0–359.
Quy ước vào/ra chung: docs/pipeline.md
"""
import numpy as np

# Tham số theo docs/TongQuanDuAn.md, hiệu chỉnh ở tuần 3
LEAF_CLOSE_KSIZE = (5, 5) # closing kernel elip để lấp lỗ trong mask lá
LESION_OPEN_KSIZE = (3, 3) # opening để xóa nhiễu điểm trên mask vết bệnh
LESION_CLOSE_KSIZE = (5, 5) # closing để nối liền ổ bệnh
HEALTHY_HUE_RANGE = (35, 85) # dải Hue của mô lá xanh khỏe (thang 0–179)


def segment_leaf(image: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Giai đoạn 2: tách phiến lá khỏi nền.

    HSV, phân ngưỡng kênh S (Otsu hoặc cv2.inRange), closing lấp lỗ.
    leaf_mask phải gồm cả vùng vết bệnh bên trong lá, nếu không infected_ratio sẽ sai.

    Trả về (leaf_mask, ảnh trung gian {SATURATION, LEAF_MASK}).
    """
    raise NotImplementedError('Thành viên 2: cài đặt segment_leaf()')


def segment_lesions(
    image: np.ndarray, leaf_mask: np.ndarray,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Giai đoạn 3: tách đốm bệnh bên trong lá.

    ROI = bitwise_and(image, leaf_mask); mask mô khỏe theo HEALTHY_HUE_RANGE (hoặc K-Means trên a*);
    lesion = leaf - healthy; opening rồi closing. lesion_mask phải nằm trọn trong leaf_mask.

    Trả về (lesion_mask, ảnh trung gian {ROI, HEALTHY_MASK, LESION_MASK_RAW, LESION_MASK}).
    """
    raise NotImplementedError('Thành viên 2: cài đặt segment_lesions()')


def measure_lesions(lesion_mask: np.ndarray) -> list[dict]:
    """Đo từng đốm bằng cv2.findContours trên lesion_mask.

    Mỗi đốm: {"area": int, "perimeter": float, "circularity": float,
    "center": [x, y], "bbox": [x, y, w, h]} — khớp cột diagnosis_histories.lesions.
    circularity = 4π·area / perimeter². Danh sách rỗng khi lá khỏe.
    """
    raise NotImplementedError('Thành viên 2: cài đặt measure_lesions()')


def draw_lesions(image: np.ndarray, lesion_mask: np.ndarray) -> np.ndarray:
    """Ảnh kết quả: vẽ đường viền đỏ quanh từng đốm bệnh lên bản sao của image."""
    raise NotImplementedError('Thành viên 2: cài đặt draw_lesions()')
