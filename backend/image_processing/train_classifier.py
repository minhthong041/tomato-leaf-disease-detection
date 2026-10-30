"""Huấn luyện, so sánh SVM với Random Forest và chốt bộ phân loại bệnh lá cà chua."""

import hashlib
import inspect
import io
import json
import time
import warnings
from pathlib import Path

import cv2
import joblib
import matplotlib
import numpy as np
from joblib import Parallel, delayed

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from . import classifier, preprocessing, segmentation
from .pipeline import RNG_SEED, load_image

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR / "dataset"
SPLITS_DIR = DATASET_DIR / "splits"
OUTPUT_DIR = BACKEND_DIR / "experiments" / "output"

VALID_SPLITS = ("train", "test")
FEATURE_CACHE_VERSION = "3c-v1"
FEATURE_N_JOBS = -1  # số tiến trình trích đặc trưng song song, -1 là dùng hết CPU

RANDOM_STATE = 42
CV_FOLDS = 5  # số fold khi tinh chỉnh siêu tham số trên tập train
SEARCH_N_JOBS = -1  # số tiến trình chạy GridSearchCV
SEARCH_SCORING = "f1_macro"
PREDICT_TIMING_SAMPLES = 200  # số ảnh test dùng để đo thời gian dự đoán một ảnh
# Ngưỡng độ tin cậy thấp: chọn sao cho bắt được ít nhất tỉ lệ này trong số dự đoán sai
LOW_CONFIDENCE_TARGET_RECALL = 0.5
LOW_CONFIDENCE_CANDIDATES = tuple(np.round(np.arange(0.30, 0.951, 0.05), 2))

MODEL_TITLES = {"svm": "SVM", "random_forest": "Random Forest"}
# Mốc so sánh: SVM tham số mặc định như 3C (#23), đo cùng cách với các model 3E
BASELINE_NAME = "svm_3c"
PLOT_TITLES = {**MODEL_TITLES, BASELINE_NAME: "SVM 3C (tham số mặc định)"}
# Siêu tham số thử khi tinh chỉnh; tham số cố định nằm trong make_model
PARAM_GRIDS = {
    "svm": {
        "svc__C": [100, 300, 1000, 3000, 10000],
        "svc__gamma": [0.003, 0.01, 0.03, 0.1],
    },
    "random_forest": {
        "n_estimators": [300],
        "max_depth": [None, 20],
        "min_samples_leaf": [1, 3],
        "max_features": ["sqrt", 0.5],
    },
}

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
    """Tạo mask lá từ ảnh đã tiền xử lý bằng segmentation.segment_leaf."""
    mask, _ = segmentation.segment_leaf(image)

    if not isinstance(mask, np.ndarray) or mask.dtype != np.uint8:
        raise ValueError("leaf_mask phải là ndarray uint8")
    if mask.shape != image.shape[:2]:
        raise ValueError("Kích thước mask không khớp ảnh")
    if not np.isin(mask, (0, 255)).all():
        raise ValueError("leaf_mask chỉ được chứa 0 và 255")
    if cv2.countNonZero(mask) == 0:
        raise ValueError("Không tìm thấy vùng lá")
    return mask


def _features_for_path(path: Path) -> np.ndarray:
    """Tiền xử lý, tách lá và trích đặc trưng cho một ảnh."""
    # Mỗi tiến trình chỉ dùng 1 luồng OpenCV để các tiến trình không giành CPU của nhau
    cv2.setNumThreads(1)
    cv2.setRNGSeed(RNG_SEED)
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
        return vector
    except Exception as exc:
        raise RuntimeError(f"Không thể trích đặc trưng ảnh: {path}") from exc


# Các hàm quyết định giá trị đặc trưng; feature_signature chỉ băm các hàm này và hằng LEAF_*.
# Sửa segmentation mà segment_leaf gọi thêm hàm phụ mới thì phải thêm vào đây, nếu không cache
# đặc trưng cũ vẫn bị dùng (test_covers_all_helpers_of_segment_leaf sẽ báo).
# Giữ tham chiếu lúc import để patch trong test không làm đổi signature.
_FEATURE_FUNCTIONS = (
    _features_for_path,
    leaf_mask_for,
    segmentation.segment_leaf,
    segmentation._refine_leaf_mask,
    segmentation._fill_largest_contour,
    segmentation._validate_image,
)


def feature_signature(paths: list[Path]) -> str:
    """Tạo signature từ phần mã ảnh hưởng tới đặc trưng và dữ liệu đầu vào.

    Chỉ băm tiền xử lý, segment_leaf (kèm hằng số LEAF_*), trích đặc trưng và
    các hàm trích đặc trưng của file này. Sửa phần huấn luyện hoặc segment_lesions
    không làm mất cache.
    """
    hasher = hashlib.sha256()
    hasher.update(FEATURE_CACHE_VERSION.encode("utf-8"))
    hasher.update(str(RNG_SEED).encode("utf-8"))

    for source in (Path(preprocessing.__file__), Path(classifier.__file__)):
        hasher.update(source.read_bytes())
    for function in _FEATURE_FUNCTIONS:
        hasher.update(inspect.getsource(function).encode("utf-8"))
    for name in sorted(vars(segmentation)):
        if name.startswith("LEAF_"):
            hasher.update(f"{name}={getattr(segmentation, name)!r}".encode("utf-8"))

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
    n_jobs: int = FEATURE_N_JOBS,
) -> tuple[np.ndarray, np.ndarray]:
    """Trích xuất đặc trưng song song và lưu cache theo tập dữ liệu."""
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

    start = time.perf_counter()
    # Parallel trả kết quả theo đúng thứ tự paths nên X và y luôn khớp nhau
    features = Parallel(n_jobs=n_jobs, verbose=5)(
        delayed(_features_for_path)(path) for path in paths
    )
    print(f"Trích đặc trưng {len(paths)} ảnh: {time.perf_counter() - start:.1f}s")

    X = np.asarray(features, dtype=np.float64)
    y = np.asarray([path.parent.name for path in paths], dtype=str)

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


def make_model(name: str = "svm", **params):
    """Tạo model chưa huấn luyện, có predict_proba, theo tên trong MODEL_TITLES."""
    if name == "svm":
        model = make_pipeline(
            StandardScaler(),
            SVC(probability=True, class_weight="balanced", random_state=RANDOM_STATE),
        )
    elif name == "random_forest":
        # Cây quyết định không cần chuẩn hóa thang đo đặc trưng
        model = RandomForestClassifier(
            class_weight="balanced", random_state=RANDOM_STATE
        )
    else:
        raise ValueError(f"Model không hợp lệ: {name}")
    return model.set_params(**params)


def _validate_training_data(X: np.ndarray, y: np.ndarray) -> None:
    if X.ndim != 2 or X.shape[1] != len(classifier.FEATURE_NAMES):
        raise ValueError("Ma trận đặc trưng không hợp lệ")
    if y.ndim != 1 or len(X) != len(y):
        raise ValueError("Số lượng đặc trưng và nhãn không khớp")
    if not np.isfinite(X).all():
        raise ValueError("Ma trận đặc trưng chứa NaN hoặc Inf")
    if len(np.unique(y)) < 2:
        raise ValueError("Cần ít nhất hai lớp để huấn luyện")


def train(X: np.ndarray, y: np.ndarray, name: str = "svm", **params):
    """Huấn luyện một model trên tập đặc trưng."""
    _validate_training_data(X, y)
    model = make_model(name, **params)
    model.fit(X, y)
    return model


def tune(
    X: np.ndarray,
    y: np.ndarray,
    name: str,
    param_grid: dict | None = None,
    cv: int = CV_FOLDS,
) -> tuple[dict, float]:
    """Tìm siêu tham số tốt nhất bằng GridSearchCV trên tập train.

    Trả về (tham số tốt nhất, macro F1 trung bình qua các fold). SVM tắt
    probability khi tìm kiếm cho nhanh; model cuối được huấn luyện lại có probability.
    """
    _validate_training_data(X, y)
    estimator = make_model(name)
    if name == "svm":
        estimator.set_params(svc__probability=False)
    search = GridSearchCV(
        estimator,
        PARAM_GRIDS[name] if param_grid is None else param_grid,
        scoring=SEARCH_SCORING,
        cv=StratifiedKFold(cv, shuffle=True, random_state=RANDOM_STATE),
        n_jobs=SEARCH_N_JOBS,
    )
    search.fit(X, y)
    return search.best_params_, float(search.best_score_)


def predict_time_ms(model, X: np.ndarray, samples: int = PREDICT_TIMING_SAMPLES) -> float:
    """Thời gian trung bình (ms) để model dự đoán một ảnh, gọi predict_proba từng ảnh."""
    rows = X[: max(1, min(samples, len(X)))]
    start = time.perf_counter()
    for row in rows:
        model.predict_proba(row.reshape(1, -1))
    return (time.perf_counter() - start) / len(rows) * 1000


def model_size_bytes(model) -> int:
    """Kích thước model khi lưu bằng joblib, tính trong bộ nhớ."""
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    return buffer.getbuffer().nbytes


def suggest_confidence_threshold(
    confidences: np.ndarray,
    correct: np.ndarray,
    target_recall: float = LOW_CONFIDENCE_TARGET_RECALL,
    candidates: tuple = LOW_CONFIDENCE_CANDIDATES,
) -> dict:
    """Chọn ngưỡng nhỏ nhất bắt được ít nhất target_recall số dự đoán sai.

    Ảnh có độ tin cậy dưới ngưỡng bị cảnh báo. Trả về ngưỡng, tỉ lệ ảnh bị cảnh báo,
    tỉ lệ dự đoán sai bị bắt, accuracy của các ảnh không bị cảnh báo và target_reached.
    Không ngưỡng nào đạt target_recall thì trả ngưỡng lớn nhất, target_reached=False
    và phát cảnh báo.
    """
    confidences = np.asarray(confidences, dtype=np.float64)
    correct = np.asarray(correct, dtype=bool)
    if confidences.shape != correct.shape or confidences.ndim != 1 or not len(correct):
        raise ValueError("confidences và correct phải là mảng 1 chiều cùng độ dài")

    wrong = ~correct
    chosen = None
    for threshold in candidates:
        flagged = confidences < threshold
        recall = float(flagged[wrong].mean()) if wrong.any() else 1.0
        chosen = {
            "threshold": float(threshold),
            "flagged_ratio": float(flagged.mean()),
            "wrong_caught": recall,
            "accepted_accuracy": (
                float(correct[~flagged].mean()) if (~flagged).any() else 0.0
            ),
        }
        if recall >= target_recall:
            chosen["target_reached"] = True
            return chosen
    # Không ngưỡng nào đạt mục tiêu: vẫn trả ngưỡng lớn nhất nhưng báo rõ
    chosen["target_reached"] = False
    warnings.warn(
        f"Không ngưỡng nào bắt được {target_recall:.0%} dự đoán sai; "
        f"dùng ngưỡng lớn nhất {chosen['threshold']:.2f}"
    )
    return chosen


def plot_confidence(
    confidences: np.ndarray,
    correct: np.ndarray,
    threshold: float,
    title: str,
    out_path: Path,
) -> None:
    """Vẽ histogram độ tin cậy của dự đoán đúng và sai, kèm đường ngưỡng."""
    fig, ax = plt.subplots(figsize=(8, 5))
    try:
        bins = np.linspace(0, 1, 21)
        ax.hist(confidences[correct], bins=bins, alpha=0.6, label="Dự đoán đúng")
        ax.hist(confidences[~correct], bins=bins, alpha=0.6, label="Dự đoán sai")
        ax.axvline(threshold, color="black", linestyle="--", label=f"Ngưỡng {threshold:.2f}")
        ax.set_title(title)
        ax.set_xlabel("Độ tin cậy (xác suất lớn nhất)")
        ax.set_ylabel("Số ảnh")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
    finally:
        plt.close(fig)


def evaluate(
    model,
    X: np.ndarray,
    y: np.ndarray,
    out_dir: Path = OUTPUT_DIR,
    name: str = "svm",
) -> dict:
    """Đánh giá mô hình và lưu confusion_matrix_<name>.png."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = list(model.classes_)
    # Giống classifier.predict trên web: lấy lớp có xác suất cao nhất
    predictions = model.classes_[model.predict_proba(X).argmax(axis=1)]
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
        ax.set_title(f"Ma trận nhầm lẫn - {PLOT_TITLES.get(name, name)}")
        ax.set_xlabel("Nhãn dự đoán")
        ax.set_ylabel("Nhãn thực tế")
        fig.tight_layout()
        fig.savefig(
            out_dir / f"confusion_matrix_{name}.png", dpi=150, bbox_inches="tight"
        )
    finally:
        plt.close(fig)

    return {
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "per_class_f1": {label: float(report[label]["f1-score"]) for label in labels},
    }


def _load_features() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
    return X_train, y_train, X_test, y_test


def main() -> None:
    """So sánh SVM với Random Forest, lưu model tốt hơn và đề xuất ngưỡng tin cậy."""
    start = time.perf_counter()
    X_train, y_train, X_test, y_test = _load_features()

    # Mốc 3C: cùng đặc trưng, tham số mặc định, đo cùng cách với các model 3E
    print(f"Huấn luyện mốc {PLOT_TITLES[BASELINE_NAME]}...")
    baseline = train(X_train, y_train, "svm")
    baseline_metrics = evaluate(baseline, X_test, y_test, name=BASELINE_NAME)
    baseline_metrics["model_bytes"] = model_size_bytes(baseline)

    results = {}
    models = {}
    for name in MODEL_TITLES:
        print(f"Tinh chỉnh {MODEL_TITLES[name]}...")
        tune_start = time.perf_counter()
        params, cv_macro_f1 = tune(X_train, y_train, name)
        tune_seconds = time.perf_counter() - tune_start
        print(f"  Tham số tốt nhất: {params}, macro F1 (CV): {cv_macro_f1:.4f}")

        train_start = time.perf_counter()
        model = train(X_train, y_train, name, **params)
        train_seconds = time.perf_counter() - train_start

        metrics = evaluate(model, X_test, y_test, name=name)
        metrics.update(
            best_params=params,
            cv_macro_f1=cv_macro_f1,
            tune_seconds=round(tune_seconds, 2),
            train_seconds=round(train_seconds, 2),
            predict_ms_per_image=round(predict_time_ms(model, X_test), 3),
            model_bytes=model_size_bytes(model),
        )
        print(
            f"  Test accuracy: {metrics['accuracy']:.4f}, "
            f"macro F1: {metrics['macro_f1']:.4f}"
        )
        results[name] = metrics
        models[name] = model

    # Chọn theo macro F1 trên CV của tập train, không nhìn tập test
    chosen = max(results, key=lambda name: results[name]["cv_macro_f1"])
    model = models[chosen]
    params = results[chosen]["best_params"]
    print(f"Chọn {MODEL_TITLES[chosen]}")

    # Ngưỡng tin cậy tính trên dự đoán ngoài fold của tập train, kiểm tra lại trên test
    print("Tính ngưỡng độ tin cậy...")
    oof_proba = cross_val_predict(
        make_model(chosen, **params),
        X_train,
        y_train,
        cv=StratifiedKFold(CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
        method="predict_proba",
        n_jobs=SEARCH_N_JOBS,
    )
    classes = np.unique(y_train)
    oof_correct = classes[oof_proba.argmax(axis=1)] == y_train
    threshold = suggest_confidence_threshold(oof_proba.max(axis=1), oof_correct)

    test_proba = model.predict_proba(X_test)
    test_confidence = test_proba.max(axis=1)
    test_correct = model.classes_[test_proba.argmax(axis=1)] == y_test
    test_flagged = test_confidence < threshold["threshold"]
    threshold["test_flagged_ratio"] = float(test_flagged.mean())
    threshold["test_wrong_caught"] = (
        float(test_flagged[~test_correct].mean()) if (~test_correct).any() else 1.0
    )
    threshold["test_accepted_accuracy"] = (
        float(test_correct[~test_flagged].mean()) if (~test_flagged).any() else 0.0
    )
    plot_confidence(
        test_confidence,
        test_correct,
        threshold["threshold"],
        f"Độ tin cậy trên tập test - {MODEL_TITLES[chosen]}",
        OUTPUT_DIR / "confidence_histogram.png",
    )

    classifier.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, classifier.MODEL_PATH)

    summary = {
        "chosen_model": chosen,
        "baseline_3c": baseline_metrics,
        "models": results,
        "low_confidence": threshold,
        "train_samples": len(y_train),
        "test_samples": len(y_test),
        "total_seconds": round(time.perf_counter() - start, 2),
        "model_path_bytes": classifier.MODEL_PATH.stat().st_size,
        "feature_cache_version": FEATURE_CACHE_VERSION,
        "segmentation_sha256": hashlib.sha256(
            Path(segmentation.__file__).read_bytes()
        ).hexdigest(),
    }
    metrics_path = OUTPUT_DIR / "model_comparison.json"
    metrics_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"{PLOT_TITLES[BASELINE_NAME]}: accuracy {baseline_metrics['accuracy']:.4f}, "
        f"macro F1 {baseline_metrics['macro_f1']:.4f}"
    )
    for name, metrics in results.items():
        print(
            f"{MODEL_TITLES[name]}: accuracy {metrics['accuracy']:.4f}, "
            f"macro F1 {metrics['macro_f1']:.4f}, "
            f"{metrics['predict_ms_per_image']:.2f} ms/ảnh, "
            f"{metrics['model_bytes'] / 1e6:.2f} MB"
        )
    print(
        f"Ngưỡng tin cậy đề xuất: {threshold['threshold']:.2f} "
        f"(test: cảnh báo {threshold['test_flagged_ratio']:.1%} ảnh, "
        f"bắt {threshold['test_wrong_caught']:.1%} dự đoán sai)"
    )
    print(f"Model: {classifier.MODEL_PATH}")
    print(f"Metrics: {metrics_path}")


if __name__ == "__main__":
    main()
