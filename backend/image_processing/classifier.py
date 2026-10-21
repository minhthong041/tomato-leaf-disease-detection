"""Giai đoạn 4 — Trích xuất đặc trưng và phân loại tên bệnh. Phụ trách: Thành viên 3.

Model là một estimator của scikit-learn có predict_proba (ví dụ Pipeline(StandardScaler, SVC(probability=True))
hoặc RandomForestClassifier), huấn luyện với nhãn là mã lớp PlantVillage (trùng diseases.code),
lưu bằng joblib.dump(model, MODEL_PATH).
Quy ước vào/ra chung: docs/pipeline.md
"""

from functools import lru_cache
from pathlib import Path

import cv2
import joblib
import numpy as np
from scipy.stats import skew
from skimage.feature import graycomatrix, graycoprops

MODEL_PATH = Path(__file__).resolve().parent / "models" / "classifier.joblib"

# Tham số GLCM (skimage.feature.graycomatrix / graycoprops)
GLCM_DISTANCES = (1,)
GLCM_ANGLES = (0, np.pi / 4, np.pi / 2, 3 * np.pi / 4)
GLCM_PROPS = ("contrast", "dissimilarity", "homogeneity", "energy", "correlation")
# Lượng tử hóa mức xám của lá về 1..GLCM_LEVELS; mức GLCM_BACKGROUND_LEVEL dành riêng cho nền
GLCM_LEVELS = 32
GLCM_BACKGROUND_LEVEL = 0

# Color Moments trên 3 kênh HSV
COLOR_CHANNELS = ("h", "s", "v")
COLOR_MOMENTS = ("mean", "std", "skew")
# std nhỏ hơn ngưỡng này coi như kênh đồng màu: skewness không xác định, gán 0
STD_EPSILON = 1e-6

# Thứ tự đặc trưng trong vector: 5 GLCM (trung bình 4 góc) rồi 9 Color Moments
FEATURE_NAMES = tuple(f"glcm_{prop}" for prop in GLCM_PROPS) + tuple(
    f"{channel}_{moment}" for channel in COLOR_CHANNELS for moment in COLOR_MOMENTS
)


def _glcm_features(gray: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """5 thuộc tính GLCM_PROPS của vùng lá trên ảnh xám.

    Mức xám của lá được lượng tử hóa về 1..GLCM_LEVELS, nền gán GLCM_BACKGROUND_LEVEL.
    Sau khi tính graycomatrix, bỏ hàng và cột của mức nền nên mọi cặp điểm có dính nền
    đều bị loại: nền không ảnh hưởng tới kết quả.

    Xử lý 4 góc GLCM_ANGLES: lấy trung bình mỗi thuộc tính trên 4 góc (còn 5 giá trị)
    để đặc trưng gần bất biến với hướng xoay của lá trong ảnh.
    """
    # Ép kiểu uint16 trước khi nhân để không tràn số
    quantized = (gray.astype(np.uint16) * (GLCM_LEVELS - 1) // 255 + 1).astype(np.uint8)
    quantized[leaf_mask == 0] = GLCM_BACKGROUND_LEVEL

    glcm = graycomatrix(
        quantized,
        GLCM_DISTANCES,
        GLCM_ANGLES,
        levels=GLCM_LEVELS + 1,
        symmetric=True,
    )
    # Bỏ hàng và cột của mức nền; graycoprops tự chuẩn hóa ma trận còn lại
    keep = np.arange(GLCM_LEVELS + 1) != GLCM_BACKGROUND_LEVEL
    glcm = glcm[keep][:, keep].astype(np.float64)

    return np.array(
        [graycoprops(glcm, prop).mean() for prop in GLCM_PROPS], dtype=np.float64
    )


def _color_moments(hsv: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """Mean, std, skewness trên từng kênh H, S, V, chỉ lấy các điểm có leaf_mask = 255.

    Thứ tự: h_mean, h_std, h_skew, s_mean, ..., v_skew. Kênh H tính tuyến tính trên thang 0–179:
    màu lá cà chua (xanh, vàng, nâu) không chạm điểm nối 0/179 của vòng Hue.
    Kênh đồng màu (std ≈ 0) có skewness gán 0.
    """
    pixels = hsv[leaf_mask == 255].astype(np.float64)  # shape (N, 3)
    mean = pixels.mean(axis=0)
    std = pixels.std(axis=0)

    skewness = np.zeros(len(COLOR_CHANNELS), dtype=np.float64)
    varying = std > STD_EPSILON
    if varying.any():
        skewness[varying] = skew(pixels[:, varying], axis=0)

    return np.column_stack([mean, std, skewness]).ravel()


def extract_features(image: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """Vector đặc trưng 1 chiều float64, độ dài len(FEATURE_NAMES), của vùng lá.

    Gồm GLCM_PROPS trên ảnh xám (trung bình 4 góc) và Color Moments (mean, std, skewness)
    trên 3 kênh H, S, V, chỉ tính trên các điểm ảnh có leaf_mask = 255.
    Thứ tự đặc trưng theo FEATURE_NAMES, phải giống lúc huấn luyện. Không sửa ảnh vào.

    Ném ValueError khi ảnh hoặc mask sai quy ước, hoặc mask rỗng.
    """
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"image phải là ảnh BGR uint8 (H, W, 3), nhận {image.dtype} {image.shape}"
        )
    if leaf_mask.dtype != np.uint8 or leaf_mask.shape != image.shape[:2]:
        raise ValueError(
            f"leaf_mask phải là uint8 kích thước {image.shape[:2]}, nhận {leaf_mask.dtype} {leaf_mask.shape}"
        )
    if cv2.countNonZero(leaf_mask) == 0:
        raise ValueError("leaf_mask rỗng, không có điểm ảnh lá để trích đặc trưng")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    features = np.concatenate(
        [_glcm_features(gray, leaf_mask), _color_moments(hsv, leaf_mask)]
    )
    # correlation của GLCM ra NaN khi vùng lá đồng nhất -> gán 0 để model không lỗi
    return np.nan_to_num(features, nan=0.0).astype(np.float64)


@lru_cache(maxsize=1)
def load_model(path: Path = MODEL_PATH):
    return joblib.load(path)


def predict(features: np.ndarray) -> tuple[str, float]:
    """Trả về (mã lớp PlantVillage, xác suất của lớp đó trong [0, 1])."""
    model = load_model()
    proba = model.predict_proba(features.reshape(1, -1))[0]
    best = int(np.argmax(proba))
    return str(model.classes_[best]), float(proba[best])
