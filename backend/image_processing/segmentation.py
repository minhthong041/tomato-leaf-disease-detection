"""Giai đoạn 2 và 3 — Tách lá, tách đốm bệnh và đo diện tích.

Mask là ảnh xám uint8 cùng kích thước với ảnh vào, chỉ gồm 0 (nền) và 255
(vùng được chọn). Kênh H của HSV trong OpenCV chạy 0–179.
Quy ước vào/ra chung: docs/pipeline.md
"""
import cv2
import numpy as np

from . import steps

# Tham số theo docs/TongQuanDuAn.md, hiệu chỉnh ở tuần 3
LEAF_CLOSE_KSIZE = (5, 5)
LESION_OPEN_KSIZE = (3, 3)
LESION_CLOSE_KSIZE = (5, 5)
HEALTHY_HUE_RANGE = (35, 85)


def _validate_image(image: np.ndarray, name: str = 'image') -> None:
    if not isinstance(image, np.ndarray):
        raise TypeError(f'{name} phải là np.ndarray')
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f'{name} phải là ảnh BGR uint8 có shape (H, W, 3)')
    if image.shape[0] == 0 or image.shape[1] == 0:
        raise ValueError(f'{name} không được rỗng')


def _validate_mask(mask: np.ndarray, shape: tuple[int, int], name: str) -> None:
    if not isinstance(mask, np.ndarray) or mask.dtype != np.uint8 or mask.shape != shape:
        raise ValueError(f'{name} phải là mask uint8 có shape {shape}')
    if not np.isin(mask, (0, 255)).all():
        raise ValueError(f'{name} chỉ được chứa giá trị 0 và 255')


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    """Lấp các vùng nền khép kín bên trong mask nhị phân."""
    padded = np.pad(mask, 1, mode='constant', constant_values=0)
    cv2.floodFill(padded, None, (0, 0), 255)
    holes = cv2.bitwise_not(padded)[1:-1, 1:-1]
    return cv2.bitwise_or(mask, holes)


def _largest_component(mask: np.ndarray) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if count <= 1:
        return np.zeros_like(mask)
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(labels == largest_label, 255, 0).astype(np.uint8)


def segment_leaf(image: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Tách toàn bộ phiến lá bằng Otsu trên độ bão hòa HSV và closing."""
    _validate_image(image)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    _, leaf_mask = cv2.threshold(
        saturation, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU,
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, LEAF_CLOSE_KSIZE)
    leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
    leaf_mask = _largest_component(leaf_mask)
    leaf_mask = _fill_holes(leaf_mask)

    return leaf_mask, {
        steps.SATURATION: saturation,
        steps.LEAF_MASK: leaf_mask,
    }


def segment_lesions(
    image: np.ndarray, leaf_mask: np.ndarray,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Tách mô không xanh khỏe trong phiến lá và lọc nhiễu hình thái học."""
    _validate_image(image)
    _validate_mask(leaf_mask, image.shape[:2], 'leaf_mask')

    roi = cv2.bitwise_and(image, image, mask=leaf_mask)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    healthy_mask = cv2.inRange(
        hsv,
        np.array((HEALTHY_HUE_RANGE[0], 0, 0), dtype=np.uint8),
        np.array((HEALTHY_HUE_RANGE[1], 255, 255), dtype=np.uint8),
    )
    healthy_mask = cv2.bitwise_and(healthy_mask, leaf_mask)
    lesion_mask_raw = cv2.bitwise_and(leaf_mask, cv2.bitwise_not(healthy_mask))

    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, LESION_OPEN_KSIZE)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, LESION_CLOSE_KSIZE)
    lesion_mask = cv2.morphologyEx(lesion_mask_raw, cv2.MORPH_OPEN, open_kernel)
    lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, close_kernel)
    lesion_mask = cv2.bitwise_and(lesion_mask, leaf_mask)

    return lesion_mask, {
        steps.ROI: roi,
        steps.HEALTHY_MASK: healthy_mask,
        steps.LESION_MASK_RAW: lesion_mask_raw,
        steps.LESION_MASK: lesion_mask,
    }


def measure_lesions(lesion_mask: np.ndarray) -> list[dict]:
    """Đo diện tích contour, chu vi, circularity, tâm và bounding box từng đốm."""
    if not isinstance(lesion_mask, np.ndarray) or lesion_mask.ndim != 2:
        raise ValueError('lesion_mask phải là ảnh xám 2 chiều')
    if lesion_mask.dtype != np.uint8:
        raise ValueError('lesion_mask phải có dtype uint8')
    if not np.isin(lesion_mask, (0, 255)).all():
        raise ValueError('lesion_mask chỉ được chứa giá trị 0 và 255')

    contours, _ = cv2.findContours(
        lesion_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )
    lesions = []
    for contour in contours:
        area = int(cv2.contourArea(contour))
        perimeter = float(cv2.arcLength(contour, True))
        moments = cv2.moments(contour)
        if moments['m00']:
            center = [
                int(round(moments['m10'] / moments['m00'])),
                int(round(moments['m01'] / moments['m00'])),
            ]
        else:
            x, y, width, height = cv2.boundingRect(contour)
            center = [x + width // 2, y + height // 2]
        x, y, width, height = cv2.boundingRect(contour)
        circularity = (4 * np.pi * area / perimeter ** 2) if perimeter else 0.0
        lesions.append({
            'area': area,
            'perimeter': perimeter,
            'circularity': float(circularity),
            'center': center,
            'bbox': [x, y, width, height],
        })
    return lesions


def draw_lesions(image: np.ndarray, lesion_mask: np.ndarray) -> np.ndarray:
    """Vẽ viền đỏ quanh các vùng bệnh trên một bản sao của ảnh BGR."""
    _validate_image(image)
    if not isinstance(lesion_mask, np.ndarray) or lesion_mask.ndim != 2:
        raise ValueError('lesion_mask phải là ảnh xám 2 chiều')
    if lesion_mask.dtype != np.uint8:
        raise ValueError('lesion_mask phải có dtype uint8')
    if not np.isin(lesion_mask, (0, 255)).all():
        raise ValueError('lesion_mask chỉ được chứa giá trị 0 và 255')

    if lesion_mask.shape != image.shape[:2]:
        lesion_mask = cv2.resize(
            lesion_mask,
            (image.shape[1], image.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )
    contours, _ = cv2.findContours(
        lesion_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )
    contour_img = image.copy()
    cv2.drawContours(contour_img, contours, -1, (0, 0, 255), 2)
    return contour_img


def process_image(
    preprocessed_img: np.ndarray, original_img: np.ndarray | None = None,
) -> dict[str, np.ndarray | int | float]:
    """Chạy segmentation và trả kết quả dạng dict cho ứng dụng gọi trực tiếp.

    Các hàm theo giai đoạn ở trên vẫn là giao diện được ``pipeline.py`` sử dụng.
    ``severity_ratio`` tính theo phần trăm; khi không tìm thấy lá, tỷ lệ là 0.0.
    """
    _validate_image(preprocessed_img, 'preprocessed_img')
    if original_img is not None:
        _validate_image(original_img, 'original_img')

    mask_leaf, _ = segment_leaf(preprocessed_img)
    mask_lesion, lesion_steps = segment_lesions(preprocessed_img, mask_leaf)
    mask_healthy = lesion_steps[steps.HEALTHY_MASK]
    area_leaf = int(cv2.countNonZero(mask_leaf))
    area_lesion = int(cv2.countNonZero(mask_lesion))
    severity_ratio = (area_lesion / area_leaf * 100.0) if area_leaf else 0.0

    return {
        'mask_leaf': mask_leaf,
        'mask_healthy': mask_healthy,
        'mask_lesion': mask_lesion,
        'contour_img': draw_lesions(original_img if original_img is not None else preprocessed_img, mask_lesion),
        'area_leaf': area_leaf,
        'area_lesion': area_lesion,
        'severity_ratio': float(severity_ratio),
    }
