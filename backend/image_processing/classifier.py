"""Giai đoạn 4 — Trích xuất đặc trưng và phân loại tên bệnh. Phụ trách: Thành viên 3.

Model là một estimator của scikit-learn có predict_proba (ví dụ Pipeline(StandardScaler, SVC(probability=True))
hoặc RandomForestClassifier), huấn luyện với nhãn là mã lớp PlantVillage (trùng diseases.code),
lưu bằng joblib.dump(model, MODEL_PATH).
Quy ước vào/ra chung: docs/pipeline.md
"""
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / 'models' / 'classifier.joblib'

# Tham số GLCM (skimage.feature.graycomatrix / graycoprops)
GLCM_DISTANCES = (1,)
GLCM_ANGLES = (0, np.pi / 4, np.pi / 2, 3 * np.pi / 4)
GLCM_PROPS = ('contrast', 'dissimilarity', 'homogeneity', 'energy', 'correlation')


def extract_features(image: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """Vector đặc trưng 1 chiều (float) của vùng lá.

    Gồm GLCM_PROPS trên ảnh xám và Color Moments (mean, std, skewness) trên 3 kênh H, S, V,
    chỉ tính trên các điểm ảnh có leaf_mask = 255. Thứ tự đặc trưng phải giống lúc huấn luyện.
    """
    raise NotImplementedError('Thành viên 3: cài đặt extract_features()')


@lru_cache(maxsize=1)
def load_model(path: Path = MODEL_PATH):
    return joblib.load(path)


def predict(features: np.ndarray) -> tuple[str, float]:
    """Trả về (mã lớp PlantVillage, xác suất của lớp đó trong [0, 1])."""
    model = load_model()
    proba = model.predict_proba(features.reshape(1, -1))[0]
    best = int(np.argmax(proba))
    return str(model.classes_[best]), float(proba[best])
