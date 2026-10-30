"""Chọn bộ ảnh mẫu cho demo (việc 4I).

Chạy từ thư mục backend/ (cần ảnh PlantVillage trong dataset/plantvillage/):
    python experiments/pick_demo_images.py
    python experiments/pick_demo_images.py --per-class 30   # thử nhiều ảnh hơn mỗi lớp

Bộ ảnh gồm:
- mỗi lớp một ảnh: mô hình đoán đúng lớp, không có cảnh báo nào trên trang kết quả, độ tin cậy cao nhất
  trong số ảnh đã thử;
- một ảnh cho ra cảnh báo độ tin cậy thấp (ưu tiên ảnh mô hình đoán sai, để demo luôn nút "Báo kết quả sai");
- một ảnh không dùng được: ảnh tự tạo không có lá, pipeline báo lỗi "Không tìm thấy lá trong ảnh".

Chỉ lấy ảnh trong tập test (dataset/splits/test.txt): mô hình chưa thấy ảnh này lúc huấn luyện.
Ảnh được chép vào experiments/output/demo/ (không đưa lên git) kèm demo_images.csv; bảng Markdown in ra
để dán vào docs/demo.md. Quy tắc cảnh báo giống frontend/src/constants/diagnosis.js (resultWarnings).
"""
import argparse
import csv
import random
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from django.core.files import File  # noqa: E402

from api.images import strip_image_metadata  # noqa: E402
from image_processing import pipeline  # noqa: E402
from image_processing.errors import PipelineError  # noqa: E402

DATASET_DIR = BACKEND_DIR / 'dataset'
TEST_SPLIT = DATASET_DIR / 'splits' / 'test.txt'
OUTPUT_DIR = BACKEND_DIR / 'experiments' / 'output' / 'demo'

# Trùng frontend/src/constants/diagnosis.js
LOW_CONFIDENCE_THRESHOLD = 0.55
HEALTHY_CODE = 'Tomato___healthy'
NO_LESION_DISEASE_CODES = ('Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus')

DEFAULT_PER_CLASS = 20
SEED = 42
UNUSABLE_NAME = '12_khong_dung_duoc.png'
CSV_COLUMNS = ('file', 'vai_tro', 'anh_goc', 'lop_that', 'du_doan', 'do_tin_cay', 'cap', 'canh_bao', 'loi')


def warnings_for(code: str, confidence: float, level: int) -> list[str]:
    """Các cảnh báo trang kết quả sẽ hiện (giống resultWarnings ở frontend)."""
    warnings = []
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        warnings.append('do_tin_cay_thap')
    healthy = code == HEALTHY_CODE
    if healthy and level >= 1:
        warnings.append('la_khoe_co_vet_benh')
    elif not healthy and level == 0 and code not in NO_LESION_DISEASE_CODES:
        warnings.append('benh_nhung_cap_0')
    return warnings


def load_test_paths(split_file: Path) -> dict[str, list[Path]]:
    """{mã lớp: [đường dẫn ảnh]} từ test.txt (mỗi dòng: plantvillage/<mã lớp>/<tên ảnh>)."""
    by_class: dict[str, list[Path]] = {}
    for line in split_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        relative = Path(line)
        by_class.setdefault(relative.parent.name, []).append(DATASET_DIR / relative)
    return by_class


def load_as_web(path: Path) -> np.ndarray:
    """Đọc ảnh đúng như web: xóa EXIF và lưu lại (JPG chất lượng 95) như api/images.py, rồi giải mã.

    Lưu lại JPG làm điểm ảnh đổi nhẹ; ảnh sát ngưỡng có thể cho kết quả khác hẳn đọc thẳng file gốc,
    nên phải đọc như web thì bảng trong docs/demo.md mới khớp màn hình lúc demo.
    """
    with open(path, 'rb') as f:
        cleaned = strip_image_metadata(File(f, name=path.name))
    image = cv2.imdecode(np.frombuffer(cleaned.read(), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise PipelineError('Không đọc được ảnh. Hãy tải lên ảnh JPG hoặc PNG.')
    return image


def diagnose(path: Path) -> dict:
    """Chạy pipeline như trên web, trả một dòng kết quả."""
    row = {'anh_goc': str(path.relative_to(DATASET_DIR)), 'lop_that': path.parent.name, 'loi': ''}
    try:
        result = pipeline.run(load_as_web(path))
    except PipelineError as exc:
        row['loi'] = str(exc)
        return row
    row.update(
        du_doan=result.disease_code,
        do_tin_cay=round(float(result.disease_confidence), 4),
        cap=int(result.severity_level),
    )
    row['canh_bao'] = warnings_for(result.disease_code, row['do_tin_cay'], row['cap'])
    return row


def pick_class_image(rows: list[dict]) -> dict | None:
    """Ảnh đoán đúng, không cảnh báo, độ tin cậy cao nhất."""
    good = [r for r in rows if not r['loi'] and r['du_doan'] == r['lop_that'] and not r['canh_bao']]
    return max(good, key=lambda r: r['do_tin_cay'], default=None)


def pick_low_confidence(rows: list[dict]) -> dict | None:
    """Ảnh có cảnh báo độ tin cậy thấp; ưu tiên ảnh đoán sai, rồi độ tin cậy gần ngưỡng nhất (không quá vô lý)."""
    low = [r for r in rows if not r['loi'] and 'do_tin_cay_thap' in r['canh_bao']]
    return max(low, key=lambda r: (r['du_doan'] != r['lop_that'], r['do_tin_cay']), default=None)


def make_unusable_image(size: int = 512) -> np.ndarray:
    """Ảnh mặt bàn xám xanh có nhiễu, không có lá: pipeline phải báo không tìm thấy lá."""
    rng = np.random.default_rng(SEED)
    gradient = np.linspace(90, 150, size, dtype=np.float32)[None, :, None]
    base = np.broadcast_to(gradient, (size, size, 1)) * np.array([1.0, 0.9, 0.8], np.float32)
    noisy = base + rng.normal(0, 6, (size, size, 3))
    return np.clip(noisy, 0, 255).astype(np.uint8)


def write_image(path: Path, image: np.ndarray) -> None:
    ok, buffer = cv2.imencode(path.suffix, image)
    if not ok:
        raise OSError(f'Không ghi được ảnh {path}')
    buffer.tofile(str(path))  # tofile thay cho cv2.imwrite để ghi được vào đường dẫn có dấu


def markdown_table(chosen: list[dict]) -> str:
    lines = [
        '| File | Vai trò | Lớp thật | Kết quả | Độ tin cậy | Cấp | Cảnh báo |',
        '|---|---|---|---|---:|---:|---|',
    ]
    for r in chosen:
        result = r['loi'] or r.get('du_doan', '')
        confidence = '' if r['loi'] else f"{r['do_tin_cay']:.2f}".replace('.', ',')
        level = '' if r['loi'] else r['cap']
        warnings = ', '.join(r.get('canh_bao') or []) or ('lỗi' if r['loi'] else 'không')
        lines.append(
            f"| `{r['file']}` | {r['vai_tro']} | {r.get('lop_that', '')} | {result} | {confidence} | {level} | {warnings} |"
        )
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--per-class', type=int, default=DEFAULT_PER_CLASS, help='số ảnh test thử mỗi lớp')
    parser.add_argument('--out', type=Path, default=OUTPUT_DIR, help='thư mục chép ảnh đã chọn')
    args = parser.parse_args(argv)

    listed = load_test_paths(TEST_SPLIT)
    # Bỏ ảnh có trong test.txt mà không có trên máy (bộ ảnh chép thiếu)
    by_class = {code: [p for p in paths if p.exists()] for code, paths in listed.items()}
    empty = [code for code, paths in by_class.items() if not paths]
    if empty:
        print(f'Không thấy ảnh nào của {", ".join(empty)}. '
              f'Giải nén PlantVillage vào {DATASET_DIR / "plantvillage"}.', file=sys.stderr)
        return 1
    for code, paths in by_class.items():
        if len(paths) < len(listed[code]):
            print(f'Cảnh báo: {code} thiếu {len(listed[code]) - len(paths)}/{len(listed[code])} ảnh test',
                  file=sys.stderr)

    rng = random.Random(SEED)
    all_rows, chosen = [], []
    for number, code in enumerate(sorted(by_class), start=1):
        sample = rng.sample(by_class[code], min(args.per_class, len(by_class[code])))
        print(f'[{number}/{len(by_class)}] {code}: thử {len(sample)} ảnh...', flush=True)
        rows = [diagnose(path) for path in sample]
        all_rows.extend(rows)
        best = pick_class_image(rows)
        if best is None:
            print(f'  Cảnh báo: không có ảnh nào đoán đúng mà không bị cảnh báo; thử --per-class lớn hơn',
                  file=sys.stderr)
            continue
        chosen.append({**best, 'file': f'{number:02d}_{code.removeprefix("Tomato___")}{Path(best["anh_goc"]).suffix.lower()}',
                       'vai_tro': 'mỗi lớp một ảnh'})

    low = pick_low_confidence(all_rows)
    if low is None:
        print('Cảnh báo: không có ảnh nào dưới ngưỡng độ tin cậy; thử --per-class lớn hơn', file=sys.stderr)
    else:
        chosen.append({**low, 'file': f'11_do_tin_cay_thap{Path(low["anh_goc"]).suffix.lower()}',
                       'vai_tro': 'cảnh báo độ tin cậy thấp'})

    out_dir = Path(args.out)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for r in chosen:
        shutil.copyfile(DATASET_DIR / r['anh_goc'], out_dir / r['file'])

    unusable = make_unusable_image()
    write_image(out_dir / UNUSABLE_NAME, unusable)
    try:
        pipeline.run(unusable)
        error = ''
    except PipelineError as exc:
        error = str(exc)
    if not error:
        print('Cảnh báo: ảnh không có lá vẫn chạy qua pipeline, cần chọn ảnh lỗi khác', file=sys.stderr)
    chosen.append({'file': UNUSABLE_NAME, 'vai_tro': 'ảnh không dùng được', 'anh_goc': '(ảnh tự tạo, không có lá)',
                   'lop_that': '', 'loi': error or '(không lỗi)'})

    with open(out_dir / 'demo_images.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for r in chosen:
            writer.writerow({**r, 'canh_bao': ', '.join(r.get('canh_bao') or [])})

    print(f'\nĐã chép {len(chosen)} ảnh vào {out_dir}\n')
    print(markdown_table(chosen))
    return 0


if __name__ == '__main__':
    sys.exit(main())
