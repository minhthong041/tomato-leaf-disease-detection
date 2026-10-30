"""Đánh giá tách lá, tách vết bệnh và cấp độ so với mask tô tay (việc 1D). Phụ trách: Thành viên 1.

Chạy từ thư mục backend/ (cần ảnh PlantVillage và bộ mask chuẩn trong dataset/):
    python experiments/evaluate.py
Bảng từng ảnh ghi vào experiments/output/evaluate.csv; bảng trung bình theo lớp in ra dạng Markdown.
Thêm --overlay để lưu hình so sánh từng ảnh vào experiments/output/evaluate/ (xem draw_overlay):
    python experiments/evaluate.py --overlay

Bộ mask chuẩn
- 30 ảnh trong dataset/splits/ground_truth.txt (3 ảnh mỗi lớp, chọn ngẫu nhiên từ test.txt, seed 42).
- Mask đặt ở dataset/masks/leaf/<tên ảnh>.png và dataset/masks/lesion/<tên ảnh>.png, cùng cỡ ảnh gốc
  PlantVillage (256x256), uint8 chỉ gồm 0/255, vết bệnh luôn nằm trong lá. Bộ mask chia sẻ qua Drive.
- Mask lá: lấy từ ảnh tách nền chính thức của PlantVillage (raw/segmented), kiểm tra bằng mắt cả 30 ảnh
  và vá tay 6 ảnh bị thiếu mép cháy.
- Mask vết bệnh: Thành viên 1 tô tay theo quy tắc:
  - tô mô đổi màu rõ (nâu, đen, xám, vàng đậm), gồm cả mảng mô chết lớn và mép lá cháy;
  - không tô quầng vàng nhạt quanh đốm;
  - nhện đỏ: tô vùng loang lổ hoặc vàng thấy rõ;
  - lá khỏe: mask trống;
  - virus (xoăn vàng lá, khảm): triệu chứng là lá biến dạng, không có vùng đổi màu nhìn thấy được trên
    ảnh 256x256, nên mask trống. Trống ở đây là "không có vùng đổi màu", không phải lá khỏe.

Cách tính
- Ảnh đi qua tiền xử lý, segment_leaf và segment_lesions như pipeline.run(), không chạy bộ phân loại.
  Mask chuẩn được phóng lên 512x512 bằng INTER_NEAREST cho khớp ảnh sau tiền xử lý.
- S% = số điểm vết bệnh / số điểm lá * 100, cấp tính bằng severity.severity_level() trên số điểm ảnh,
  giống pipeline. Sai số S = S dự đoán - S thật, đơn vị điểm %.
- Ảnh có mask vết bệnh chuẩn trống thì IoU/Dice vết bệnh không có ý nghĩa (chỉ cần pipeline thấy 1 điểm
  là ra 0): để trống hai cột này và không tính vào trung bình. Với các ảnh đó, S dự đoán > 0 nghĩa là
  pipeline nhận nhầm vết bệnh.
- Ảnh có S thật cách ngưỡng cấp (5%, 15%, 35%) dưới NEAR_THRESHOLD_PP điểm % được đánh dấu sat_nguong:
  lệch cấp ở các ảnh này chủ yếu do sai số tô tay chứ chưa chắc do pipeline.
"""
import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
# Chạy bằng "python experiments/evaluate.py" thì backend/ chưa có trong sys.path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from image_processing import pipeline, preprocessing, segmentation, severity  # noqa: E402
from image_processing.errors import PipelineError  # noqa: E402

DATASET_DIR = BACKEND_DIR / 'dataset'
GROUND_TRUTH_FILE = DATASET_DIR / 'splits' / 'ground_truth.txt'
MASKS_DIR = DATASET_DIR / 'masks'
OUTPUT_FILE = BACKEND_DIR / 'experiments' / 'output' / 'evaluate.csv'
OVERLAY_DIR = BACKEND_DIR / 'experiments' / 'output' / 'evaluate'

# Ngưỡng S% giữa các cấp, khớp severity.severity_level()
SEVERITY_THRESHOLDS = (5, 15, 35)
NEAR_THRESHOLD_PP = 1.0
CLASS_PREFIX = 'Tomato___'

# Màu BGR của hình so sánh: đúng (có ở cả dự đoán và mask chuẩn), báo nhầm (chỉ có ở dự đoán),
# bỏ sót (chỉ có ở mask chuẩn)
COLOR_CORRECT = (0, 200, 0)
COLOR_FALSE_ALARM = (0, 0, 255)
COLOR_MISSED = (255, 140, 0)
OVERLAY_ALPHA = 0.6
# Vùng ngoài lá chuẩn được làm tối đi để dễ nhìn vết bệnh
OUTSIDE_LEAF_DIM = 0.4
HEADER_HEIGHT = 56
FOOTER_HEIGHT = 30

CSV_COLUMNS = (
    'anh', 'lop', 'iou_la', 'iou_vet_benh', 'dice_vet_benh', 's_that', 's_du_doan', 'sai_so_s',
    'cap_that', 'cap_du_doan', 'sat_nguong', 'loi',
)


@dataclass
class GroundTruth:
    path: Path # ảnh gốc
    disease: str # tên thư mục lớp, trùng diseases.code
    leaf_mask: np.ndarray # 512x512, 0/255
    lesion_mask: np.ndarray # 512x512, 0/255


def iou(pred: np.ndarray, truth: np.ndarray) -> float:
    """Intersection over Union của hai mask 0/255 cùng kích thước. Cả hai rỗng thì trả 1.0."""
    pred, truth = pred > 0, truth > 0
    union = np.count_nonzero(pred | truth)
    if union == 0:
        return 1.0
    return np.count_nonzero(pred & truth) / union


def dice(pred: np.ndarray, truth: np.ndarray) -> float:
    """Hệ số Dice (2|A∩B| / (|A|+|B|)) của hai mask 0/255 cùng kích thước. Cả hai rỗng thì trả 1.0."""
    pred, truth = pred > 0, truth > 0
    total = np.count_nonzero(pred) + np.count_nonzero(truth)
    if total == 0:
        return 1.0
    return 2 * np.count_nonzero(pred & truth) / total


def _read_mask(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f'Thiếu mask chuẩn: {path}')
    mask = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise ValueError(f'Không đọc được mask: {path}')
    if not np.isin(mask, (0, 255)).all():
        raise ValueError(f'Mask chỉ được chứa giá trị 0 và 255: {path}')
    size = (preprocessing.TARGET_SIZE, preprocessing.TARGET_SIZE)
    return cv2.resize(mask, size, interpolation=cv2.INTER_NEAREST)


def load_ground_truth(list_file: Path = GROUND_TRUTH_FILE, masks_dir: Path = MASKS_DIR) -> list[GroundTruth]:
    """Đọc danh sách ảnh chuẩn và hai mask của từng ảnh, mask đã phóng lên 512x512.

    Mỗi dòng của list_file là đường dẫn ảnh tương đối tính từ thư mục cha của splits/ (dataset/).
    """
    list_file = Path(list_file)
    dataset_dir = list_file.parent.parent
    items = []
    for line in list_file.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        path = dataset_dir / line
        if not path.is_file():
            raise FileNotFoundError(f'Không tìm thấy ảnh: {path}')
        name = f'{path.stem}.png'
        leaf_mask = _read_mask(Path(masks_dir) / 'leaf' / name)
        lesion_mask = _read_mask(Path(masks_dir) / 'lesion' / name)
        if np.count_nonzero((lesion_mask > 0) & (leaf_mask == 0)):
            raise ValueError(f'Mask vết bệnh có điểm nằm ngoài mask lá: {name}')
        items.append(GroundTruth(path, path.parent.name, leaf_mask, lesion_mask))
    return items


def predict_masks(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(leaf_mask, lesion_mask) do pipeline dự đoán, cùng các bước như pipeline.run()."""
    # Cùng seed GrabCut với pipeline.run(): mask mỗi ảnh khớp kết quả trên web và không phụ thuộc
    # ảnh nào chạy trước nó trong danh sách
    cv2.setRNGSeed(pipeline.RNG_SEED)
    processed, _ = preprocessing.preprocess(image)
    leaf_mask, _ = segmentation.segment_leaf(processed)
    lesion_mask, _ = segmentation.segment_lesions(processed, leaf_mask)
    return leaf_mask, lesion_mask


def infected_percent(lesion_mask: np.ndarray, leaf_mask: np.ndarray) -> float:
    leaf_area = cv2.countNonZero(leaf_mask)
    return 100 * cv2.countNonZero(lesion_mask) / leaf_area if leaf_area else 0.0


def is_near_threshold(percent: float) -> bool:
    return any(abs(percent - threshold) < NEAR_THRESHOLD_PP for threshold in SEVERITY_THRESHOLDS)


def evaluate_image(leaf_true: np.ndarray, lesion_true: np.ndarray,
                   leaf_pred: np.ndarray, lesion_pred: np.ndarray) -> dict:
    """Chỉ số của một ảnh. Mask vết bệnh chuẩn trống thì iou_vet_benh và dice_vet_benh là None."""
    s_true = infected_percent(lesion_true, leaf_true)
    leaf_pred_area = cv2.countNonZero(leaf_pred)
    s_pred = infected_percent(lesion_pred, leaf_pred)
    has_lesion = cv2.countNonZero(lesion_true) > 0
    return {
        'iou_la': iou(leaf_pred, leaf_true),
        'iou_vet_benh': iou(lesion_pred, lesion_true) if has_lesion else None,
        'dice_vet_benh': dice(lesion_pred, lesion_true) if has_lesion else None,
        's_that': s_true,
        's_du_doan': s_pred,
        'sai_so_s': s_pred - s_true,
        'cap_that': severity.severity_level(cv2.countNonZero(lesion_true), cv2.countNonZero(leaf_true)),
        # Pipeline báo lỗi khi không thấy lá; ở đây ghi cấp trống để vẫn so được các chỉ số khác
        'cap_du_doan': (severity.severity_level(cv2.countNonZero(lesion_pred), leaf_pred_area)
                        if leaf_pred_area else None),
        'sat_nguong': is_near_threshold(s_true),
    }


def color_comparison(base: np.ndarray, pred: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Tô lên ảnh BGR các điểm đúng, báo nhầm và bỏ sót của mask dự đoán so với mask chuẩn."""
    out = base.copy()
    pred, truth = pred > 0, truth > 0
    for pixels, color in ((pred & truth, COLOR_CORRECT), (pred & ~truth, COLOR_FALSE_ALARM),
                          (~pred & truth, COLOR_MISSED)):
        out[pixels] = ((1 - OVERLAY_ALPHA) * out[pixels] + OVERLAY_ALPHA * np.array(color)).astype(np.uint8)
    return out


def _put_text(image: np.ndarray, text: str, origin: tuple[int, int], background: bool = False) -> None:
    """Chữ trắng; background=True vẽ thêm nền đen phía sau để đọc được khi chữ nằm trên ảnh sáng."""
    if background:
        (width, height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        x, y = origin
        cv2.rectangle(image, (x - 4, y - height - 4), (x + width + 4, y + baseline + 2), (0, 0, 0), cv2.FILLED)
    cv2.putText(image, text, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)


def draw_overlay(image: np.ndarray, leaf_true: np.ndarray, lesion_true: np.ndarray,
                 leaf_pred: np.ndarray, lesion_pred: np.ndarray, title: str = '',
                 row: dict | None = None) -> np.ndarray:
    """Hình so sánh một ảnh: ảnh gốc | so sánh mask lá | so sánh mask vết bệnh, mỗi ô cùng cỡ mask.

    image là ảnh BGR đã resize về cỡ mask (chưa CLAHE, để giữ màu thật). Ở ô vết bệnh, vùng ngoài lá
    chuẩn được làm tối. row (kết quả evaluate_image) nếu có thì in các chỉ số lên phần đầu hình.
    """
    dimmed = image.copy()
    outside = leaf_true == 0
    dimmed[outside] = (dimmed[outside] * OUTSIDE_LEAF_DIM).astype(np.uint8)
    tiles = [image, color_comparison(image, leaf_pred, leaf_true),
             color_comparison(dimmed, lesion_pred, lesion_true)]
    height, width = image.shape[:2]
    panel = np.zeros((HEADER_HEIGHT + height + FOOTER_HEIGHT, width * len(tiles), 3), np.uint8)
    panel[HEADER_HEIGHT:HEADER_HEIGHT + height] = np.hstack(tiles)

    # Font Hershey của cv2.putText chỉ vẽ được ký tự ASCII nên chữ trên hình viết không dấu
    _put_text(panel, title, (10, 22))
    if row:
        lesion = 'khong co vet benh chuan' if row['iou_vet_benh'] is None else f'IoU {row["iou_vet_benh"]:.2f}'
        level_pred = '-' if row['cap_du_doan'] is None else row['cap_du_doan']
        _put_text(panel, f'La: IoU {row["iou_la"]:.2f}  |  Vet benh: {lesion}  |  '
                         f'S that {row["s_that"]:.1f}% -> du doan {row["s_du_doan"]:.1f}%  |  '
                         f'Cap {row["cap_that"]} -> {level_pred}', (10, 46))
    for index, label in enumerate(('Anh goc', 'Mask la', 'Mask vet benh')):
        _put_text(panel, label, (index * width + 10, HEADER_HEIGHT + 22), background=True)
    legend_y = HEADER_HEIGHT + height + 21
    x = 10
    for color, label in ((COLOR_CORRECT, 'dung'), (COLOR_FALSE_ALARM, 'bao nham (thua)'),
                         (COLOR_MISSED, 'bo sot (thieu)')):
        cv2.rectangle(panel, (x, legend_y - 12), (x + 14, legend_y + 2), color, cv2.FILLED)
        _put_text(panel, label, (x + 20, legend_y))
        x += 40 + 10 * len(label)
    return panel


def save_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    success, encoded = cv2.imencode('.png', image)
    if not success:
        raise OSError(f'Không lưu được ảnh: {path}')
    encoded.tofile(str(path)) # tofile thay cho cv2.imwrite để lưu được vào đường dẫn có dấu


def evaluate_all(items: list[GroundTruth], overlay_dir: Path | None = None) -> list[dict]:
    """Một dòng mỗi ảnh. Ảnh lỗi (giai đoạn chưa cài đặt, không đọc được) ghi lý do vào cột loi.

    overlay_dir khác None thì lưu hình so sánh của từng ảnh vào đó; tên file bắt đầu bằng số thứ tự
    trong ground_truth.txt (01–30) để cả nhóm gọi ảnh theo cùng một số.
    """
    rows = []
    for number, item in enumerate(items, start=1):
        row = {'anh': item.path.name, 'lop': item.disease.removeprefix(CLASS_PREFIX), 'loi': ''}
        try:
            image = pipeline.load_image(item.path)
            leaf_pred, lesion_pred = predict_masks(image)
        except NotImplementedError as exc:
            row['loi'] = f'chưa cài đặt: {exc}'
        except PipelineError as exc:
            row['loi'] = str(exc)
        else:
            row.update(evaluate_image(item.leaf_mask, item.lesion_mask, leaf_pred, lesion_pred))
            if overlay_dir is not None:
                panel = draw_overlay(preprocessing.resize(image), item.leaf_mask, item.lesion_mask,
                                     leaf_pred, lesion_pred, f'#{number} {row["lop"]}', row)
                save_image(Path(overlay_dir) / f'{number:02d}_{row["lop"]}_{item.path.stem}.png', panel)
        if row['loi']:
            print(f'Cảnh báo: bỏ qua {item.path.name}: {row["loi"]}', file=sys.stderr)
        rows.append(row)
    return rows


def _mean(values) -> float | None:
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def summarize(rows: list[dict]) -> dict:
    """Trung bình của một nhóm dòng; bỏ qua dòng lỗi."""
    ok = [row for row in rows if not row['loi']]
    empty = [row for row in ok if row['iou_vet_benh'] is None]
    return {
        'so_anh': len(ok),
        'iou_la': _mean(row['iou_la'] for row in ok),
        'iou_vet_benh': _mean(row['iou_vet_benh'] for row in ok),
        'dice_vet_benh': _mean(row['dice_vet_benh'] for row in ok),
        'mae_s': _mean(abs(row['sai_so_s']) for row in ok),
        'dung_cap': _mean(float(row['cap_that'] == row['cap_du_doan']) for row in ok),
        'lech_toi_da_1_cap': _mean(
            float(row['cap_du_doan'] is not None and abs(row['cap_that'] - row['cap_du_doan']) <= 1)
            for row in ok
        ),
        # Ảnh không có vết bệnh chuẩn mà pipeline vẫn thấy vết bệnh
        'bao_nham': sum(row['s_du_doan'] > 0 for row in empty),
        'so_anh_trong': len(empty),
    }


def write_csv(rows: list[dict], out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig để Excel hiển thị đúng tiếng Việt
    with open(out_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _format_cell(row.get(key)) for key in CSV_COLUMNS})


def _format_cell(value) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'x' if value else ''
    if isinstance(value, float):
        return f'{value:.4f}'
    return str(value)


def _fmt(value, percent=False) -> str:
    if value is None:
        return '–'
    return f'{value:.1%}' if percent else f'{value:.3f}'


def print_summary(rows: list[dict]) -> None:
    """Bảng Markdown trung bình theo lớp và dòng tổng, để dán vào mô tả PR hoặc báo cáo."""
    print('| Lớp | Số ảnh | IoU lá | IoU vết bệnh | Dice vết bệnh | Sai số S (điểm %) | Đúng cấp '
          '| Lệch ≤ 1 cấp | Báo nhầm (ảnh không vết bệnh) |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    groups = {}
    for row in rows:
        groups.setdefault(row['lop'], []).append(row)
    for name, group in [*sorted(groups.items()), ('**Tổng**', rows)]:
        s = summarize(group)
        false_alarm = f'{s["bao_nham"]}/{s["so_anh_trong"]}' if s['so_anh_trong'] else '–'
        mae = '–' if s['mae_s'] is None else f'{s["mae_s"]:.2f}'
        print(f'| {name} | {s["so_anh"]} | {_fmt(s["iou_la"])} | {_fmt(s["iou_vet_benh"])} '
              f'| {_fmt(s["dice_vet_benh"])} | {mae} | {_fmt(s["dung_cap"], True)} '
              f'| {_fmt(s["lech_toi_da_1_cap"], True)} | {false_alarm} |')
    errors = sum(bool(row['loi']) for row in rows)
    if errors:
        print(f'\n{errors} ảnh bị bỏ qua, xem cột loi trong file CSV.')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Đánh giá tách lá, vết bệnh và cấp độ so với mask chuẩn.')
    parser.add_argument('--list', type=Path, default=GROUND_TRUTH_FILE, help='file danh sách ảnh chuẩn')
    parser.add_argument('--masks', type=Path, default=MASKS_DIR, help='thư mục chứa leaf/ và lesion/')
    parser.add_argument('--out', type=Path, default=OUTPUT_FILE, help='file CSV kết quả từng ảnh')
    parser.add_argument('--overlay', nargs='?', type=Path, const=OVERLAY_DIR, default=None,
                        help=f'lưu hình so sánh từng ảnh vào thư mục này (mặc định {OVERLAY_DIR})')
    args = parser.parse_args(argv)

    rows = evaluate_all(load_ground_truth(args.list, args.masks), args.overlay)
    write_csv(rows, args.out)
    print(f'Đã ghi {len(rows)} ảnh vào {args.out}')
    if args.overlay is not None:
        print(f'Hình so sánh lưu trong {args.overlay}')
    print()
    print_summary(rows)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
