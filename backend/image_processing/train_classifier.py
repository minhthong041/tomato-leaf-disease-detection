"""Huấn luyện bộ phân loại SVM cho bệnh lá cà chua."""

import hashlib
import json
import time
from pathlib import Path

import cv2
import joblib
import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from . import classifier, preprocessing, segmentation
from .pipeline import load_image

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR / "dataset"
SPLITS_DIR = DATASET_DIR / "splits"
OUTPUT_DIR = BACKEND_DIR / "experiments" / "output"

VALID_SPLITS = ("train", "test")
FEATURE_CACHE_VERSION = "3b-v2"
TEMP_S_THRESHOLD = 40

DISEASE_NAMES = {
    "Tomato___Bacterial_spot": "Đốm vi khuẩn",
    "Tomato___Early_blight": "Đốm vòng",
    "Tomato___Late_blight": "Mốc sương",
    "Tomato___Leaf_Mold": "Mốc lá",
    "Tomato___Septoria_leaf_spot": "Đốm lá Septoria",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Nhện đỏ hai chấm",
    "Tomato___Target_Spot": "Đốm đích",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Xoăn vàng lá",
    "Tomato___Tomato_mosaic_virus": "Khảm lá",
    "Tomato___healthy": "Lá khỏe mạnh",
}


def load_split(name: str) -> list[Path]:
    """Đọc danh sách đường dẫn ảnh từ tập train hoặc test."""
    if name not in VALID_SPLITS:
        raise ValueError(f"Split không hợp lệ: {name}")

    split_file = SPLITS_DIR / f"{name}.txt"
    lines = split_file.read_text(encoding="utf-8-sig").splitlines()
    return [DATASET_DIR / Path(line.strip()) for line in lines if line.strip()]


def leaf_mask_for(image: np.ndarray) -> np.ndarray:
    """Tạo mask lá từ ảnh đã tiền xử lý."""
    try:
        mask, _ = segmentation.segment_leaf(image)
    except NotImplementedError:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        _, mask = cv2.threshold(hsv[:, :, 1], TEMP_S_THRESHOLD, 255, cv2.THRESH_BINARY)

    if not isinstance(mask, np.ndarray) or mask.dtype != np.uint8:
        raise ValueError("leaf_mask phải là ndarray uint8")
    if mask.shape != image.shape[:2]:
        raise ValueError("Kích thước mask không khớp ảnh")
    if not np.isin(mask, (0, 255)).all():
        raise ValueError("leaf_mask chỉ được chứa 0 và 255")
    if cv2.countNonZero(mask) == 0:
        raise ValueError("Không tìm thấy vùng lá")
    return mask


def feature_signature(paths: list[Path]) -> str:
    """Tạo signature từ mã xử lý ảnh và dữ liệu đầu vào."""
    hasher = hashlib.sha256()
    hasher.update(FEATURE_CACHE_VERSION.encode("utf-8"))

    for source in (
        Path(__file__),
        Path(preprocessing.__file__),
        Path(segmentation.__file__),
        Path(classifier.__file__),
    ):
        hasher.update(source.read_bytes())

    for path in paths:
        hasher.update(str(path.resolve()).encode("utf-8"))
        stat = path.stat()
        hasher.update(str(stat.st_size).encode("utf-8"))
        hasher.update(str(stat.st_mtime_ns).encode("utf-8"))

    return hasher.hexdigest()


def build_features(
    paths: list[Path],
    split: str | None = None,
    use_cache: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Trích xuất đặc trưng và lưu cache theo tập dữ liệu."""
    paths = [Path(path) for path in paths]
    if not paths:
        raise ValueError("Danh sách ảnh rỗng")
    if split not in (None, "train", "test", "smoke"):
        raise ValueError(f"Split cache không hợp lệ: {split}")

    signature = feature_signature(paths) if split is not None else None
    cache_path = OUTPUT_DIR / f"features_{split}.npz" if split else None

    if use_cache and cache_path is not None and cache_path.exists():
        try:
            with np.load(cache_path, allow_pickle=False) as cached:
                X_cached = cached["X"]
                y_cached = cached["y"]
                valid = (
                    cached["signature"].item() == signature
                    and X_cached.shape == (len(paths), len(classifier.FEATURE_NAMES))
                    and y_cached.shape == (len(paths),)
                    and np.array_equal(
                        cached["paths"],
                        np.asarray([str(path) for path in paths]),
                    )
                    and np.array_equal(
                        y_cached, np.asarray([path.parent.name for path in paths])
                    )
                    and np.isfinite(X_cached).all()
                )
                if valid:
                    print(f"Sử dụng cache: {cache_path}")
                    return X_cached, y_cached
        except (OSError, ValueError, KeyError, EOFError):
            pass

    features = []
    labels = []
    start = time.perf_counter()

    for index, path in enumerate(paths, start=1):
        try:
            image = load_image(path)
            processed, _ = preprocessing.preprocess(image)
            mask = leaf_mask_for(processed)
            vector = np.asarray(
                classifier.extract_features(processed, mask), dtype=np.float64
            )
            if vector.shape != (len(classifier.FEATURE_NAMES),):
                raise ValueError(f"Vector đặc trưng sai kích thước: {vector.shape}")
            if not np.isfinite(vector).all():
                raise ValueError("Vector đặc trưng chứa NaN hoặc Inf")
            features.append(vector)
            labels.append(path.parent.name)
        except Exception as exc:
            raise RuntimeError(f"Không thể trích đặc trưng ảnh: {path}") from exc

        if index % 100 == 0 or index == len(paths):
            print(f"[{index}/{len(paths)}] {time.perf_counter() - start:.1f}s")

    X = np.asarray(features, dtype=np.float64)
    y = np.asarray(labels, dtype=str)

    if cache_path is not None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            cache_path,
            X=X,
            y=y,
            paths=np.asarray([str(path) for path in paths]),
            signature=np.asarray(signature),
        )
        print(f"Đã lưu cache: {cache_path}")

    return X, y


def train(X: np.ndarray, y: np.ndarray):
    """Huấn luyện bộ phân loại SVM trên tập đặc trưng."""
    if X.ndim != 2 or X.shape[1] != len(classifier.FEATURE_NAMES):
        raise ValueError("Ma trận đặc trưng không hợp lệ")
    if y.ndim != 1 or len(X) != len(y):
        raise ValueError("Số lượng đặc trưng và nhãn không khớp")
    if not np.isfinite(X).all():
        raise ValueError("Ma trận đặc trưng chứa NaN hoặc Inf")
    if len(np.unique(y)) < 2:
        raise ValueError("Cần ít nhất hai lớp để huấn luyện")

    model = make_pipeline(
        StandardScaler(),
        SVC(probability=True, class_weight="balanced", random_state=42),
    )
    model.fit(X, y)
    return model


def evaluate(
    model,
    X: np.ndarray,
    y: np.ndarray,
    out_dir: Path = OUTPUT_DIR,
) -> dict:
    """Đánh giá mô hình và lưu confusion matrix."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = list(model.classes_)
    predictions = model.predict(X)
    accuracy = accuracy_score(y, predictions)
    macro_f1 = f1_score(y, predictions, labels=labels, average="macro", zero_division=0)
    report = classification_report(
        y, predictions, labels=labels, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y, predictions, labels=labels)

    fig, ax = plt.subplots(figsize=(14, 12))
    try:
        display = ConfusionMatrixDisplay(
            confusion_matrix=matrix,
            display_labels=[DISEASE_NAMES.get(label, label) for label in labels],
        )
        display.plot(
            ax=ax,
            cmap="Blues",
            xticks_rotation=45,
            values_format="d",
            colorbar=False,
        )
        ax.set_title("Ma trận nhầm lẫn - SVM")
        ax.set_xlabel("Nhãn dự đoán")
        ax.set_ylabel("Nhãn thực tế")
        fig.tight_layout()
        fig.savefig(out_dir / "confusion_matrix.png", dpi=150, bbox_inches="tight")
    finally:
        plt.close(fig)

    return {
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "per_class_f1": {label: float(report[label]["f1-score"]) for label in labels},
    }


def main() -> None:
    """Huấn luyện và đánh giá SVM trên dataset PlantVillage."""
    start = time.perf_counter()
    train_paths = load_split("train")
    test_paths = load_split("test")

    for name, paths in (("train", train_paths), ("test", test_paths)):
        if not paths:
            raise ValueError(f"Split {name} rỗng")
        if len({path.resolve() for path in paths}) != len(paths):
            raise ValueError(f"Split {name} chứa ảnh trùng")

    if {path.resolve() for path in train_paths} & {
        path.resolve() for path in test_paths
    }:
        raise ValueError("Train và test có ảnh trùng nhau")

    print(f"Train: {len(train_paths)} ảnh")
    print(f"Test: {len(test_paths)} ảnh")
    X_train, y_train = build_features(train_paths, split="train")
    X_test, y_test = build_features(test_paths, split="test")

    if set(y_test) - set(y_train):
        raise ValueError("Test chứa lớp không có trong train")

    print("Huấn luyện SVM...")
    train_start = time.perf_counter()
    model = train(X_train, y_train)
    train_seconds = time.perf_counter() - train_start

    print("Đánh giá mô hình...")
    metrics = evaluate(model, X_test, y_test)

    classifier.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, classifier.MODEL_PATH)

    metrics["train_samples"] = len(y_train)
    metrics["test_samples"] = len(y_test)
    metrics["train_seconds"] = round(train_seconds, 2)
    metrics["total_seconds"] = round(time.perf_counter() - start, 2)
    metrics["model_bytes"] = classifier.MODEL_PATH.stat().st_size
    metrics["feature_cache_version"] = FEATURE_CACHE_VERSION
    metrics["segmentation_sha256"] = hashlib.sha256(
        Path(segmentation.__file__).read_bytes()
    ).hexdigest()

    metrics_path = OUTPUT_DIR / "svm_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"Model: {classifier.MODEL_PATH}")
    print(f"Metrics: {metrics_path}")


if __name__ == "__main__":
    main()
