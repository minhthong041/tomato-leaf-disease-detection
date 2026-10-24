"""Huấn luyện SVM (3B); chạy từ backend bằng python -m image_processing.train_classifier."""

import argparse
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
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from . import classifier, preprocessing, segmentation

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = BACKEND_DIR / "dataset"
SPLITS_DIR = DATASET_DIR / "splits"
OUTPUT_DIR = BACKEND_DIR / "experiments" / "output"
MODEL_PATH = classifier.MODEL_PATH
# Ngưỡng cho thí nghiệm mới, không khẳng định là ngưỡng của model cũ.
TEMP_S_THRESHOLD = 30
RANDOM_STATE = 42
PROGRESS_INTERVAL = 250
FIGURE_SIZE = (14, 11)
FIGURE_DPI = 200
MASK_MODE = "auto"
VI_LABELS = {
    "Tomato___Bacterial_spot": "Đốm vi khuẩn",
    "Tomato___Early_blight": "Cháy lá sớm",
    "Tomato___healthy": "Lá khỏe",
    "Tomato___Late_blight": "Cháy lá muộn",
    "Tomato___Leaf_Mold": "Mốc lá",
    "Tomato___Septoria_leaf_spot": "Đốm lá Septoria",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Nhện đỏ hai chấm",
    "Tomato___Target_Spot": "Đốm vòng",
    "Tomato___Tomato_mosaic_virus": "Virus khảm cà chua",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Virus xoăn vàng lá",
}


def load_split(name: str) -> list[Path]:
    """Đọc từng đường dẫn nguyên dòng, giữ dấu cách trong tên file."""
    if name not in ("train", "test"):
        raise ValueError("name phải là 'train' hoặc 'test'")
    lines = (SPLITS_DIR / f"{name}.txt").read_text(encoding="utf-8-sig").splitlines()
    return [DATASET_DIR / line.strip() for line in lines if line.strip()]


def _temporary_mask(image):
    """Mask HSV tạm cho 3B; xóa phần này khi chốt 3C sau việc 2A."""
    saturation = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)[:, :, 1]
    _, mask = cv2.threshold(saturation, TEMP_S_THRESHOLD, 255, cv2.THRESH_BINARY)
    return mask


def leaf_mask_for(image: np.ndarray) -> np.ndarray:
    """Lấy mask chính thức; fallback chỉ khi TV2 chưa cài đặt hàm.

    Chế độ temp cho phép tái lập thí nghiệm 3B ngay cả khi 2A đã merge.
    Không fallback khi segmentation trả mask sai hoặc phát sinh lỗi khác.
    """
    if MASK_MODE == "temp":
        mask = _temporary_mask(image)
    else:
        try:
            mask, _ = segmentation.segment_leaf(image)
        except NotImplementedError:
            if MASK_MODE == "segmentation":
                raise
            mask = _temporary_mask(image)
    if not isinstance(mask, np.ndarray) or mask.dtype != np.uint8:
        raise ValueError("Mask phải là ndarray uint8")
    if mask.shape != image.shape[:2] or not np.isin(mask, (0, 255)).all():
        raise ValueError("Mask phải cùng kích thước ảnh, chỉ chứa 0/255")
    if cv2.countNonZero(mask) == 0:
        raise ValueError("Không tìm thấy vùng lá")
    return mask


def build_features(paths: list[Path], split: str | None = None):
    """Tiền xử lý → mask → đặc trưng; split=None không đọc/ghi cache."""
    paths = [Path(path) for path in paths]
    if not paths:
        raise ValueError("Danh sách ảnh rỗng")
    if split not in (None, "train", "test"):
        raise ValueError("split phải là train, test hoặc None")
    cache_file = OUTPUT_DIR / f"features_{split}.npz" if split else None
    signature = None
    if cache_file is not None:
        # Giữ cơ chế cache đơn giản; bao gồm chế độ mask và script train.
        digest = hashlib.sha256()
        for source in (
            Path(__file__),
            Path(preprocessing.__file__),
            Path(segmentation.__file__),
            Path(classifier.__file__),
        ):
            digest.update(source.read_bytes())
        digest.update(MASK_MODE.encode("utf-8"))
        digest.update(
            json.dumps([str(p) for p in paths], ensure_ascii=False).encode("utf-8")
        )
        signature = digest.hexdigest()
        if cache_file.exists():
            try:
                with np.load(cache_file, allow_pickle=False) as cache:
                    X, y = cache["X"], cache["y"]
                    if (
                        cache["signature"].item() == signature
                        and X.shape == (len(paths), len(classifier.FEATURE_NAMES))
                        and y.shape == (len(paths),)
                        and np.isfinite(X).all()
                        and np.array_equal(y, [p.parent.name for p in paths])
                    ):
                        print(f"Đọc cache: {cache_file}")
                        return X, y
            except (OSError, ValueError, KeyError):
                print("Cache không hợp lệ, tính lại.")
    features, labels = [], []
    for index, path in enumerate(paths, start=1):
        try:
            image = cv2.imdecode(
                np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR
            )
            if image is None:
                raise ValueError("Không đọc được ảnh")
            processed, _ = preprocessing.preprocess(image)
            mask = leaf_mask_for(processed)
            vector = np.asarray(classifier.extract_features(processed, mask))
            if (
                vector.shape != (len(classifier.FEATURE_NAMES),)
                or not np.isfinite(vector).all()
            ):
                raise ValueError("Vector đặc trưng sai kích thước hoặc chứa NaN/Inf")
        except Exception as exc:
            raise RuntimeError(f"Lỗi ảnh {index}/{len(paths)}: {path}") from exc
        features.append(vector)
        labels.append(path.parent.name)
        if index % PROGRESS_INTERVAL == 0 or index == len(paths):
            print(f"[{split or 'custom'}] {index}/{len(paths)}", flush=True)
    X, y = np.asarray(features, dtype=np.float64), np.asarray(labels, dtype=str)
    if cache_file is not None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache_file, X=X, y=y, signature=np.asarray(signature))
    return X, y


def train(X, y):
    """Huấn luyện scaler và SVM chỉ bằng dữ liệu train."""
    model = make_pipeline(
        StandardScaler(),
        SVC(probability=True, class_weight="balanced", random_state=RANDOM_STATE),
    )
    model.fit(X, y)
    return model


def evaluate(model, X, y, out_dir):
    """Lưu accuracy, F1 từng lớp, macro F1 và confusion matrix tiếng Việt."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    predicted = model.predict(X)
    labels = list(model.classes_)
    report = classification_report(
        y, predicted, labels=labels, output_dict=True, zero_division=0
    )
    report["accuracy"] = float(accuracy_score(y, predicted))
    text = classification_report(y, predicted, labels=labels, digits=4, zero_division=0)
    print(f"Accuracy: {report['accuracy']:.4f}")
    print(f"Macro F1: {report['macro avg']['f1-score']:.4f}\n{text}")
    (out_dir / "classification_report.txt").write_text(text, encoding="utf-8")
    (out_dir / "classification_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    try:
        ConfusionMatrixDisplay(
            confusion_matrix(y, predicted, labels=labels),
            display_labels=[VI_LABELS.get(label, label) for label in labels],
        ).plot(
            ax=ax, cmap="Blues", xticks_rotation=45, values_format="d", colorbar=False
        )
        ax.set_title("Ma trận nhầm lẫn - Phân loại bệnh lá cà chua")
        ax.set_xlabel("Nhãn dự đoán")
        ax.set_ylabel("Nhãn thực tế")
        fig.tight_layout()
        fig.savefig(
            out_dir / "confusion_matrix.png", dpi=FIGURE_DPI, bbox_inches="tight"
        )
    finally:
        plt.close(fig)
    return report


def main():
    """Chạy thí nghiệm; mặc định lưu model tại classifier.MODEL_PATH."""
    global MASK_MODE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mask", choices=("auto", "temp", "segmentation"), default="auto"
    )
    args = parser.parse_args()
    MASK_MODE = args.mask
    started = time.perf_counter()
    print(f"Mask mode: {MASK_MODE}; TEMP_S_THRESHOLD: {TEMP_S_THRESHOLD}", flush=True)
    if MASK_MODE == "auto":
        print("Auto: gọi TV2, chỉ dùng mask tạm nếu gặp NotImplementedError.")
    train_paths, test_paths = load_split("train"), load_split("test")
    for name, paths in (("train", train_paths), ("test", test_paths)):
        if not paths or len({p.resolve() for p in paths}) != len(paths):
            raise ValueError(f"Split {name} rỗng hoặc chứa đường dẫn trùng")
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(path)
    if {p.resolve() for p in train_paths} & {p.resolve() for p in test_paths}:
        raise ValueError("Train và test có đường dẫn trùng nhau")
    print(f"Train: {len(train_paths)}; Test: {len(test_paths)}", flush=True)
    X_train, y_train = build_features(train_paths, "train")
    X_test, y_test = build_features(test_paths, "test")
    if set(y_test) - set(y_train):
        raise ValueError("Test có lớp không tồn tại trong train")
    print("Đang huấn luyện SVM...", flush=True)
    model = train(X_train, y_train)
    report = evaluate(model, X_test, y_test, OUTPUT_DIR)
    model_path = Path(MODEL_PATH)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    elapsed = time.perf_counter() - started
    summary = {
        "mask_mode": MASK_MODE,
        "temporary_s_threshold": (
            TEMP_S_THRESHOLD if MASK_MODE != "segmentation" else None
        ),
        "train_samples": len(y_train),
        "test_samples": len(y_test),
        "classes": list(model.classes_),
        "runtime_seconds": elapsed,
        "model_bytes": model_path.stat().st_size,
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "segmentation_sha256": hashlib.sha256(
            Path(segmentation.__file__).read_bytes()
        ).hexdigest(),
    }
    (OUTPUT_DIR / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Model: {model_path}; {summary['model_bytes']} byte")
    print(f"Tổng thời gian: {elapsed / 60:.2f} phút")


if __name__ == "__main__":
    main()
