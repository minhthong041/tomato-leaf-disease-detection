"""Giai đoạn 2 và 3 — Tách lá, tách đốm bệnh và đo diện tích.

``leaf_mask`` chứa toàn bộ diện tích lá, bao gồm cả đốm bệnh.
``lesion_mask`` chỉ chứa đốm nằm hoàn toàn bên trong ``leaf_mask``.
Các mask là ảnh xám uint8 cùng kích thước ảnh, chỉ gồm 0 và 255.
Các trường kết quả diện tích dùng tên cột database ``leaf_area_px`` và
``lesion_area_px``; ``infected_ratio`` có cùng quy ước tỷ lệ 0–1 với pipeline.
Quy ước vào/ra chung: docs/pipeline.md
"""
import cv2
import numpy as np

from . import steps
from .errors import PipelineError

# Tham số morphology và ngưỡng màu (kênh H của OpenCV nằm trong khoảng 0–179).
LEAF_CLOSE_KSIZE = (5, 5)
LEAF_GREEN_LOWER = (25, 40, 30)
LEAF_GREEN_UPPER = (95, 255, 255)
LEAF_GRABCUT_FG_RADIUS = 40
LEAF_GRABCUT_BG_RADIUS = 65
LEAF_GRABCUT_ITERATIONS = 5
LEAF_WARM_EDGE_RESTORE_RADIUS = 20
LEAF_WARM_MIN_SATURATION = 50
LEAF_WARM_MIN_VALUE = 40
LESION_OPEN_KSIZE = (3, 3)
LESION_CLOSE_KSIZE = (5, 5)
LESION_EDGE_MARGIN_PX = 5
HEALTHY_HUE_RANGE = (35, 85)
HEALTHY_MIN_SATURATION = 25
HEALTHY_MIN_VALUE = 30
LESION_MIN_SATURATION = 25
LESION_MIN_AREA_PX = 12


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


def _fill_largest_contour(mask: np.ndarray) -> np.ndarray:
    """Tô contour ngoài và giữ mọi mảnh có diện tích từ 3% contour lớn nhất."""
    contours, _ = cv2.findContours(
        mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return np.zeros_like(mask)

    max_area = max(cv2.contourArea(contour) for contour in contours)
    filled = np.zeros_like(mask)
    for contour in contours:
        if cv2.contourArea(contour) >= 0.03 * max_area:
            cv2.drawContours(
                filled, [contour], -1, 255, thickness=cv2.FILLED,
            )
    return filled


def _refine_leaf_mask(
    image: np.ndarray, hsv: np.ndarray, green_mask: np.ndarray,
) -> np.ndarray:
    """Khôi phục mô lá gần điểm xanh và phân biệt bóng đổ ở vùng lân cận."""
    if min(image.shape[:2]) < 2 or cv2.countNonZero(green_mask) == 0:
        return green_mask

    distance = cv2.distanceTransform(
        cv2.bitwise_not(green_mask), cv2.DIST_L2, 5,
    )
    grabcut_mask = np.full(green_mask.shape, cv2.GC_BGD, dtype=np.uint8)
    grabcut_mask[distance <= LEAF_GRABCUT_BG_RADIUS] = cv2.GC_PR_BGD
    grabcut_mask[distance <= LEAF_GRABCUT_FG_RADIUS] = cv2.GC_PR_FGD
    hue, saturation, _ = cv2.split(hsv)
    warm_hue_background = (hue <= 24) | (hue >= 165)
    neutral_background = saturation < 15
    grabcut_mask[warm_hue_background] = cv2.GC_PR_BGD
    grabcut_mask[neutral_background] = cv2.GC_BGD
    grabcut_mask[green_mask > 0] = cv2.GC_FGD

    border_size = min(5, max(1, min(image.shape[:2]) // 4))
    grabcut_mask[:border_size, :] = cv2.GC_BGD
    grabcut_mask[-border_size:, :] = cv2.GC_BGD
    grabcut_mask[:, :border_size] = cv2.GC_BGD
    grabcut_mask[:, -border_size:] = cv2.GC_BGD
    grabcut_mask[green_mask > 0] = cv2.GC_FGD

    background_model = np.zeros((1, 65), dtype=np.float64)
    foreground_model = np.zeros((1, 65), dtype=np.float64)
    cv2.grabCut(
        image,
        grabcut_mask,
        None,
        background_model,
        foreground_model,
        LEAF_GRABCUT_ITERATIONS,
        cv2.GC_INIT_WITH_MASK,
    )
    refined = np.where(
        (grabcut_mask == cv2.GC_FGD) | (grabcut_mask == cv2.GC_PR_FGD),
        255,
        0,
    ).astype(np.uint8)
    warm_lesions = (
        (((hue >= 15) & (hue <= 24)) | (hue >= 165))
        & (saturation >= LEAF_WARM_MIN_SATURATION)
        & (hsv[:, :, 2] >= LEAF_WARM_MIN_VALUE)
        & (distance <= LEAF_WARM_EDGE_RESTORE_RADIUS)
    )
    refined[warm_lesions] = 255
    return refined


def segment_leaf(image: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Tách phiến lá bằng ngưỡng HSV và giữ cả vùng bệnh bên trong contour.

    Dùng ngưỡng xanh lá bão hòa cao làm foreground seed. GrabCut phục hồi vùng
    tối và cuống gần seed, đồng thời phân biệt bóng lân cận qua màu nền. Sau
    closing 5×5 và giữ/tô các contour lớn hơn 3% contour lớn nhất, các nếp gập
    nội bộ được lấp kín. Ảnh ``SATURATION`` vẫn được trả về để tương thích.
    """
    _validate_image(image)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    green_mask = cv2.inRange(
        hsv,
        np.array(LEAF_GREEN_LOWER, dtype=np.uint8),
        np.array(LEAF_GREEN_UPPER, dtype=np.uint8),
    )
    leaf_mask = _refine_leaf_mask(image, hsv, green_mask)

    closing_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, LEAF_CLOSE_KSIZE,
    )
    leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, closing_kernel)
    leaf_mask = _fill_largest_contour(leaf_mask)

    return leaf_mask, {
        steps.SATURATION: saturation,
        steps.LEAF_MASK: leaf_mask,
    }


def segment_lesions(
    image: np.ndarray, leaf_mask: np.ndarray,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Tách đốm trong lá, giới hạn màu khỏe và loại vùng nhiễu nhỏ.

    Bỏ qua vùng cách biên ``leaf_mask`` tối đa 5 pixel để hạn chế bóng đổ
    sát mép lá bị nhận nhầm thành đốm bệnh.
    ``lesion_mask`` được giao với ``leaf_mask`` lần cuối để bảo đảm mọi pixel
    đốm đều thuộc diện tích lá.
    """
    _validate_image(image)
    _validate_mask(leaf_mask, image.shape[:2], 'leaf_mask')

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    roi = cv2.bitwise_and(image, image, mask=leaf_mask)
    healthy_pixels = (
        (hue >= HEALTHY_HUE_RANGE[0])
        & (hue <= HEALTHY_HUE_RANGE[1])
        & (saturation >= HEALTHY_MIN_SATURATION)
        & (value >= HEALTHY_MIN_VALUE)
    )
    healthy_mask = np.where(healthy_pixels, 255, 0).astype(np.uint8)
    healthy_mask = cv2.bitwise_and(healthy_mask, leaf_mask)

    edge_kernel_size = LESION_EDGE_MARGIN_PX * 2 + 1
    edge_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (edge_kernel_size, edge_kernel_size),
    )
    leaf_core = cv2.erode(leaf_mask, edge_kernel)
    lesion_candidates = (
        (healthy_mask == 0)
        & (saturation >= LESION_MIN_SATURATION)
        & (value >= HEALTHY_MIN_VALUE)
        & (leaf_core > 0)
    )
    lesion_mask_raw = np.where(lesion_candidates, 255, 0).astype(np.uint8)

    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, LESION_OPEN_KSIZE)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, LESION_CLOSE_KSIZE)
    lesion_mask = cv2.morphologyEx(lesion_mask_raw, cv2.MORPH_OPEN, open_kernel)
    lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, close_kernel)
    lesion_mask = cv2.bitwise_and(lesion_mask, leaf_core)
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(
        lesion_mask, connectivity=8,
    )
    filtered_mask = np.zeros_like(lesion_mask)
    for label in range(1, component_count):
        if stats[label, cv2.CC_STAT_AREA] >= LESION_MIN_AREA_PX:
            filtered_mask[labels == label] = 255
    lesion_mask = filtered_mask

    return lesion_mask, {
        steps.ROI: roi,
        steps.HEALTHY_MASK: healthy_mask,
        steps.LESION_MASK_RAW: lesion_mask_raw,
        steps.LESION_MASK: lesion_mask,
    }


def measure_lesions(
    lesion_mask: np.ndarray,
) -> list[dict[str, int | float | list[int]]]:
    """Đo từng thành phần liên thông bằng diện tích pixel chính xác.

    ``area`` là số pixel thực thuộc đốm; chu vi và circularity được đo từ
    contour tương ứng. Tâm và bounding box dùng tọa độ ``[x, y]`` và
    ``[x, y, w, h]``. Với các đốm rất nhỏ (vài chục pixel), chỉ số
    circularity chỉ mang tính chất tham khảo.
    """
    if not isinstance(lesion_mask, np.ndarray) or lesion_mask.ndim != 2:
        raise ValueError('lesion_mask phải là ảnh xám 2 chiều')
    if lesion_mask.dtype != np.uint8:
        raise ValueError('lesion_mask phải có dtype uint8')
    if not np.isin(lesion_mask, (0, 255)).all():
        raise ValueError('lesion_mask chỉ được chứa giá trị 0 và 255')

    component_count, labels, stats, centers = cv2.connectedComponentsWithStats(
        lesion_mask, connectivity=8,
    )
    lesions = []
    for label in range(1, component_count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area == 0:
            continue
        component = np.where(labels == label, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(
            component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
        )
        contour = contours[0]
        perimeter = float(cv2.arcLength(contour, True))
        center = [int(round(centers[label][0])), int(round(centers[label][1]))]
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        circularity = (
            min(1.0, float(4 * np.pi * area / (perimeter ** 2)))
            if perimeter > 0 else 0.0
        )
        lesions.append({
            'area': area,
            'perimeter': perimeter,
            'circularity': float(circularity),
            'center': center,
            'bbox': [x, y, width, height],
        })
    return lesions


def draw_lesions(image: np.ndarray, lesion_mask: np.ndarray) -> np.ndarray:
    """Vẽ viền đỏ quanh các vùng bệnh trên ảnh BGR cùng kích thước mask."""
    _validate_image(image)
    _validate_mask(lesion_mask, image.shape[:2], 'lesion_mask')
    contours, _ = cv2.findContours(
        lesion_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )
    contour_img = image.copy()
    cv2.drawContours(contour_img, contours, -1, (0, 0, 255), 2)
    return contour_img


def process_image(
    preprocessed_img: np.ndarray, original_img: np.ndarray | None = None,
) -> dict[str, np.ndarray | int | float]:
    """Chạy segmentation độc lập và trả các trường diện tích theo pipeline.

    ``infected_ratio`` là tỷ lệ 0–1 giống ``pipeline.run()``. Nếu ảnh đầu ra
    gốc có độ phân giải khác, chỉ mask dùng để vẽ được resize tại đây; các mask
    kết quả vẫn giữ kích thước ảnh tiền xử lý.
    """
    _validate_image(preprocessed_img, 'preprocessed_img')
    if original_img is not None:
        _validate_image(original_img, 'original_img')

    mask_leaf, _ = segment_leaf(preprocessed_img)
    mask_lesion, lesion_steps = segment_lesions(preprocessed_img, mask_leaf)
    mask_healthy = lesion_steps[steps.HEALTHY_MASK]
    area_leaf = int(cv2.countNonZero(mask_leaf))
    area_lesion = int(cv2.countNonZero(mask_lesion))
    if area_leaf == 0:
        raise PipelineError('Không tìm thấy lá trong ảnh')

    contour_image = original_img if original_img is not None else preprocessed_img
    drawing_mask = mask_lesion
    if drawing_mask.shape != contour_image.shape[:2]:
        drawing_mask = cv2.resize(
            drawing_mask,
            (contour_image.shape[1], contour_image.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )

    return {
        'mask_leaf': mask_leaf,
        'mask_healthy': mask_healthy,
        'mask_lesion': mask_lesion,
        'processed_image': draw_lesions(contour_image, drawing_mask),
        'leaf_area_px': area_leaf,
        'lesion_area_px': area_lesion,
        'infected_ratio': float(area_lesion / area_leaf),
    }
