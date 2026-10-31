"""Ablation tiền xử lý (việc 1G): bỏ hoặc thay từng bước của giai đoạn 1 rồi đo lại tách lá, tách vết bệnh
và cấp độ so với mask chuẩn. Phụ trách: Thành viên 1.

Chạy từ thư mục backend/ (cần ảnh PlantVillage và bộ mask chuẩn trong dataset/, xem experiments/evaluate.py):
    python experiments/ablation.py
Bảng từng ảnh của mọi cấu hình ghi vào experiments/output/ablation.csv; bảng tổng và bảng sai số S theo lớp
in ra dạng Markdown.

Phần phân loại (cần dataset/splits/train.txt và test.txt như train_classifier; khoảng 8 giờ với 12 nhân):
    python experiments/ablation.py --classify
Kết quả ghi vào experiments/output/ablation_classification.json; đặc trưng mỗi cấu hình được cache trong
experiments/output/ablation_features/ nên chạy lại (hoặc chạy tiếp sau khi bị ngắt) không phải trích lại.

Cách làm
- Không sửa preprocessing.py: mỗi cấu hình ghép các hàm resize, denoise (Bilateral), equalize (CLAHE) của
  pipeline; Median Blur không có hàm riêng nên gọi thẳng cv2.medianBlur với preprocessing.MEDIAN_KSIZE.
- Sau tiền xử lý, ảnh đi qua evaluate.predict_masks (segment_leaf, segment_lesions, cùng seed GrabCut như
  pipeline.run()) rồi chấm bằng evaluate.evaluate_image như evaluate.py. Ảnh gốc được đọc một lần cho mọi
  cấu hình.
- Cấu hình "Bilateral + CLAHE" chính là preprocessing.preprocess(), nên dòng này trùng bảng của evaluate.py.
- Tiền xử lý ảnh hưởng cả segment_leaf (GrabCut lấy màu từ ảnh đã xử lý), nên bảng có cả IoU lá.
- Hạn chế: ngưỡng tách vết bệnh (2C) được dò trên ảnh Bilateral + CLAHE và trên chính 30 ảnh mask chuẩn này,
  nên phần phân đoạn thiên về cấu hình pipeline.
- Phần phân loại: mỗi cấu hình trích lại đặc trưng của toàn bộ train/test (tiền xử lý bằng cấu hình đó,
  segment_leaf, classifier.extract_features như train_classifier) rồi huấn luyện lại mô hình đã chốt ở 3E
  với đúng siêu tham số của models/classifier.joblib, đo accuracy và macro F1 trên test. Không tinh chỉnh
  lại siêu tham số cho từng cấu hình (lưới của 3E mất nhiều giờ), nên các cấu hình khác hơi chịu thiệt.
  Ảnh không tách được lá bị bỏ khỏi train và tính là đoán sai ở test, để mọi cấu hình chấm trên cùng số ảnh.
- Mọi cấu hình chấm trên cùng ảnh test nên so với pipeline bằng kiểm định McNemar (ghép cặp, dạng chính xác):
  đếm ảnh chỉ pipeline đúng và ảnh chỉ cấu hình kia đúng; p nhỏ (dưới 0,05) mới coi là khác thật.
"""
import argparse
import csv
import hashlib
import inspect
import json
import sys
from collections.abc import Callable
from pathlib import Path

import cv2
import joblib
import numpy as np
from joblib import Parallel, delayed
from scipy.stats import binomtest
from sklearn.base import clone
from sklearn.metrics import accuracy_score, f1_score

BACKEND_DIR = Path(__file__).resolve().parent.parent
# Chạy bằng "python experiments/ablation.py" thì backend/ chưa có trong sys.path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from experiments import evaluate  # noqa: E402
from image_processing import classifier, pipeline, preprocessing, train_classifier  # noqa: E402
from image_processing.errors import PipelineError  # noqa: E402

OUTPUT_FILE = BACKEND_DIR / 'experiments' / 'output' / 'ablation.csv'
CSV_COLUMNS = ('cau_hinh', *evaluate.CSV_COLUMNS)
CLASSIFY_FILE = BACKEND_DIR / 'experiments' / 'output' / 'ablation_classification.json'
FEATURES_DIR = BACKEND_DIR / 'experiments' / 'output' / 'ablation_features'


def _median(image: np.ndarray) -> np.ndarray:
    return cv2.medianBlur(image, preprocessing.MEDIAN_KSIZE)


# Tên cấu hình -> hàm tiền xử lý (ảnh BGR gốc -> ảnh 512x512 đưa vào segment_leaf). Cấu hình đầu là pipeline hiện tại.
CONFIGS: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    'Bilateral + CLAHE (pipeline)': lambda image: preprocessing.equalize(
        preprocessing.denoise(preprocessing.resize(image))),
    'Bilateral, bỏ CLAHE': lambda image: preprocessing.denoise(preprocessing.resize(image)),
    'Median thay Bilateral + CLAHE': lambda image: preprocessing.equalize(_median(preprocessing.resize(image))),
    'Không lọc nhiễu + CLAHE': lambda image: preprocessing.equalize(preprocessing.resize(image)),
    'Chỉ resize': preprocessing.resize,
}


def run_ablation(items: list[evaluate.GroundTruth],
                 configs: dict[str, Callable[[np.ndarray], np.ndarray]] = CONFIGS) -> dict[str, list[dict]]:
    """{tên cấu hình: các dòng như evaluate.evaluate_all}. Lỗi của một cấu hình ghi vào cột loi của dòng đó."""
    results = {name: [] for name in configs}
    for item in items:
        base = {'anh': item.path.name, 'lop': item.disease.removeprefix(evaluate.CLASS_PREFIX), 'loi': ''}
        try:
            image = pipeline.load_image(item.path)
        except PipelineError as exc:
            image, base['loi'] = None, str(exc)
        for name, prepare in configs.items():
            row = dict(base)
            if image is not None:
                try:
                    leaf_pred, lesion_pred = evaluate.predict_masks(image, prepare)
                except PipelineError as exc:
                    row['loi'] = str(exc)
                else:
                    row.update(evaluate.evaluate_image(item.leaf_mask, item.lesion_mask, leaf_pred, lesion_pred))
            if row['loi']:
                print(f'Cảnh báo: {name}: bỏ qua {item.path.name}: {row["loi"]}', file=sys.stderr)
            results[name].append(row)
    return results


def write_csv(results: dict[str, list[dict]], out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig để Excel hiển thị đúng tiếng Việt
    with open(out_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for name, rows in results.items():
            for row in rows:
                writer.writerow({'cau_hinh': name, **{key: evaluate.format_cell(row.get(key))
                                                      for key in evaluate.CSV_COLUMNS}})


def print_summary(results: dict[str, list[dict]]) -> None:
    """Bảng tổng mỗi cấu hình một dòng, rồi bảng sai số S theo lớp mỗi cấu hình một cột."""
    print('| Cấu hình | IoU lá | IoU vết bệnh | Dice vết bệnh | Sai số S (điểm %) | Đúng cấp (ảnh có vết bệnh) '
          '| Lệch ≤ 1 cấp (ảnh có vết bệnh) | Báo nhầm (ảnh mask trống) |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|')
    for name, rows in results.items():
        s = evaluate.summarize(rows)
        mae = '–' if s['mae_s'] is None else f'{s["mae_s"]:.2f}'
        print(f'| {name} | {evaluate.fmt(s["iou_la"])} | {evaluate.fmt(s["iou_vet_benh"])} '
              f'| {evaluate.fmt(s["dice_vet_benh"])} | {mae} '
              f'| {evaluate.fraction(s["dung_cap"], s["so_anh_co_vet_benh"])} '
              f'| {evaluate.fraction(s["lech_toi_da_1_cap"], s["so_anh_co_vet_benh"])} '
              f'| {evaluate.fraction(s["bao_nham"], s["so_anh_trong"])} |')

    print('\nSai số S theo lớp (điểm %):\n')
    names = list(results)
    print('| Lớp | ' + ' | '.join(names) + ' |')
    print('|---|' + '---:|' * len(names))
    classes = sorted({row['lop'] for rows in results.values() for row in rows})
    for cls in classes:
        cells = []
        for name in names:
            mae = evaluate.summarize([row for row in results[name] if row['lop'] == cls])['mae_s']
            cells.append('–' if mae is None else f'{mae:.2f}')
        print(f'| {cls} | ' + ' | '.join(cells) + ' |')

    errors = sum(bool(row['loi']) for rows in results.values() for row in rows)
    if errors:
        print(f'\n{errors} dòng bị bỏ qua, xem cột loi trong file CSV.')


def _classify_features(path: Path, prepare: Callable[[np.ndarray], np.ndarray]) -> np.ndarray | None:
    """Vector đặc trưng như train_classifier._features_for_path nhưng tiền xử lý bằng prepare.

    None nếu ảnh không đọc được hoặc không tách được lá với cấu hình này.
    """
    # Mỗi tiến trình chỉ dùng 1 luồng OpenCV để các tiến trình không giành CPU của nhau
    cv2.setNumThreads(1)
    cv2.setRNGSeed(pipeline.RNG_SEED)
    try:
        processed = prepare(pipeline.load_image(path))
        mask = train_classifier.leaf_mask_for(processed)
    except (PipelineError, ValueError):
        return None
    return np.asarray(classifier.extract_features(processed, mask), dtype=np.float64)


# Mã các hàm của file này quyết định đặc trưng, đưa vào khóa cache của config_features
_FEATURE_CODE = ''.join(inspect.getsource(function) for function in (_classify_features, _median))


def config_features(name: str, prepare: Callable[[np.ndarray], np.ndarray], paths: list[Path], split: str,
                    n_jobs: int = train_classifier.FEATURE_N_JOBS) -> tuple[np.ndarray, np.ndarray]:
    """(X, ok) của một cấu hình trên paths; ok[i] False nếu ảnh i bị bỏ (dòng X là NaN).

    Cache theo cấu hình và split; cache mất hiệu lực khi đổi danh sách ảnh, mã của prepare hoặc phần mã
    mà train_classifier.feature_signature theo dõi (tiền xử lý, segment_leaf, trích đặc trưng), kể cả
    _classify_features và _median của file này.
    """
    hasher = hashlib.sha256(train_classifier.feature_signature(paths).encode('utf-8'))
    hasher.update(name.encode('utf-8'))
    hasher.update(inspect.getsource(prepare).encode('utf-8'))
    hasher.update(_FEATURE_CODE.encode('utf-8'))
    signature = hasher.hexdigest()
    # Tên cấu hình có dấu và dấu cách nên đặt tên file theo băm của tên
    cache = FEATURES_DIR / f'{split}_{hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]}.npz'
    if cache.exists():
        with np.load(cache, allow_pickle=False) as cached:
            if cached['signature'].item() == signature:
                print(f'{name} ({split}): dùng cache {cache.name}')
                return cached['X'], cached['ok']

    print(f'{name} ({split}): trích đặc trưng {len(paths)} ảnh')
    vectors = Parallel(n_jobs=n_jobs, verbose=1)(delayed(_classify_features)(path, prepare) for path in paths)
    ok = np.array([vector is not None for vector in vectors])
    X = np.full((len(paths), len(classifier.FEATURE_NAMES)), np.nan)
    for i, vector in enumerate(vectors):
        if vector is not None:
            X[i] = vector
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, X=X, ok=ok, signature=np.asarray(signature))
    return X, ok


def run_classification(train_paths: list[Path], test_paths: list[Path],
                       configs: dict[str, Callable[[np.ndarray], np.ndarray]] = CONFIGS, model=None,
                       n_jobs: int = train_classifier.FEATURE_N_JOBS) -> dict[str, dict]:
    """{tên cấu hình: accuracy, macro F1, F1 từng lớp, số ảnh bị bỏ, McNemar so với cấu hình đầu} khi huấn
    luyện lại model trên đặc trưng của cấu hình đó. model mặc định là models/classifier.joblib (chỉ lấy siêu
    tham số, huấn luyện lại từ đầu)."""
    base = clone(joblib.load(classifier.MODEL_PATH) if model is None else model)
    y_train = np.asarray([path.parent.name for path in train_paths])
    y_test = np.asarray([path.parent.name for path in test_paths])
    results = {}
    reference = None  # đúng/sai từng ảnh test của cấu hình đầu
    for name, prepare in configs.items():
        X_train, ok_train = config_features(name, prepare, train_paths, 'train', n_jobs)
        X_test, ok_test = config_features(name, prepare, test_paths, 'test', n_jobs)
        print(f'{name}: huấn luyện trên {ok_train.sum()} ảnh')
        fitted = clone(base).fit(X_train[ok_train], y_train[ok_train])
        labels = list(fitted.classes_)
        # Ảnh bị bỏ ở test tính là đoán sai (nhãn rỗng); như web, lấy lớp có xác suất cao nhất
        predictions = np.full(len(y_test), '', dtype=y_test.dtype)
        if ok_test.any():
            predictions[ok_test] = fitted.classes_[fitted.predict_proba(X_test[ok_test]).argmax(axis=1)]
        per_class = f1_score(y_test, predictions, labels=labels, average=None, zero_division=0)
        correct = predictions == y_test
        if reference is None:
            reference, mcnemar = correct, None
        else:
            mcnemar = mcnemar_test(reference, correct)
        results[name] = {
            'accuracy': float(accuracy_score(y_test, predictions)),
            'macro_f1': float(f1_score(y_test, predictions, labels=labels, average='macro', zero_division=0)),
            'per_class_f1': {label: float(f1) for label, f1 in zip(labels, per_class)},
            'bo_qua_train': int((~ok_train).sum()),
            'bo_qua_test': int((~ok_test).sum()),
            'mcnemar': mcnemar,
        }
    return results


def mcnemar_test(reference: np.ndarray, other: np.ndarray) -> dict:
    """McNemar dạng chính xác giữa hai mảng đúng/sai trên cùng ảnh: p hai phía của kiểm định nhị thức trên các
    ảnh chỉ một bên đúng."""
    only_reference = int((reference & ~other).sum())
    only_other = int((~reference & other).sum())
    total = only_reference + only_other
    p = binomtest(only_reference, total, 0.5).pvalue if total else 1.0
    return {'chi_cau_hinh_dau_dung': only_reference, 'chi_cau_hinh_nay_dung': only_other, 'p': float(p)}


def print_classification(results: dict[str, dict]) -> None:
    """Bảng accuracy, macro F1 mỗi cấu hình một dòng, rồi bảng F1 theo lớp mỗi cấu hình một cột."""
    print('| Cấu hình | Accuracy | Macro F1 | Ảnh bị bỏ (train / test) '
          '| Chỉ cấu hình đầu đúng / chỉ cấu hình này đúng | p (McNemar) |')
    print('|---|---:|---:|---:|---:|---:|')
    for name, r in results.items():
        m = r.get('mcnemar')
        paired = '– | –' if m is None else (f'{m["chi_cau_hinh_dau_dung"]} / {m["chi_cau_hinh_nay_dung"]} '
                                             f'| {m["p"]:.3f}')
        print(f'| {name} | {r["accuracy"]:.3f} | {r["macro_f1"]:.3f} | {r["bo_qua_train"]} / {r["bo_qua_test"]} '
              f'| {paired} |')

    print('\nF1 theo lớp:\n')
    names = list(results)
    print('| Lớp | ' + ' | '.join(names) + ' |')
    print('|---|' + '---:|' * len(names))
    labels = sorted({label for r in results.values() for label in r['per_class_f1']})
    for label in labels:
        cells = [f'{results[name]["per_class_f1"].get(label, 0.0):.3f}' for name in names]
        print(f'| {label.removeprefix(evaluate.CLASS_PREFIX)} | ' + ' | '.join(cells) + ' |')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Ablation tiền xử lý: đo lại tách lá, vết bệnh và cấp độ.')
    parser.add_argument('--list', type=Path, default=evaluate.GROUND_TRUTH_FILE, help='file danh sách ảnh chuẩn')
    parser.add_argument('--masks', type=Path, default=evaluate.MASKS_DIR, help='thư mục chứa leaf/ và lesion/')
    parser.add_argument('--out', type=Path, default=None,
                        help=f'file kết quả (mặc định {OUTPUT_FILE.name}, với --classify là {CLASSIFY_FILE.name})')
    parser.add_argument('--classify', action='store_true',
                        help='đo phần phân loại trên train/test thay cho phân đoạn (khoảng 8 giờ)')
    parser.add_argument('--jobs', type=int, default=train_classifier.FEATURE_N_JOBS,
                        help='số tiến trình trích đặc trưng khi --classify, -1 là dùng hết CPU')
    args = parser.parse_args(argv)

    if args.classify:
        out = args.out or CLASSIFY_FILE
        results = run_classification(train_classifier.load_split('train'), train_classifier.load_split('test'),
                                     n_jobs=args.jobs)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Đã ghi {len(results)} cấu hình vào {out}\n')
        print_classification(results)
        return 0

    args.out = args.out or OUTPUT_FILE
    results = run_ablation(evaluate.load_ground_truth(args.list, args.masks))
    write_csv(results, args.out)
    print(f'Đã ghi {len(results)} cấu hình vào {args.out}\n')
    print_summary(results)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
