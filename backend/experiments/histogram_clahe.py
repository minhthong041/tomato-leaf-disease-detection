"""Thí nghiệm giai đoạn 1 (việc 1C): histogram kênh L trước và sau CLAHE, so sánh khử nhiễu Bilateral với Median.
Phụ trách: Thành viên 1.

Chạy từ thư mục backend/ (cần ảnh PlantVillage và bộ mask chuẩn trong dataset/, xem experiments/evaluate.py):
    python experiments/histogram_clahe.py
Mỗi lớp lấy ảnh đầu tiên của lớp đó trong dataset/splits/ground_truth.txt (10 ảnh). Hình lưu vào
experiments/output/clahe/ và experiments/output/denoise/, bảng chỉ số in ra dạng Markdown.

Cách làm
- Chỉ gọi các hàm của preprocessing.py (resize, denoise, equalize), không viết lại thuật toán. Median Blur
  không có hàm riêng trong pipeline nên gọi thẳng cv2.medianBlur với preprocessing.MEDIAN_KSIZE.
- CLAHE: ảnh "trước" là ảnh đã resize và lọc Bilateral, đúng đầu vào của equalize() trong pipeline.
  Histogram tính trên vùng lá (mask lá chuẩn) để nền xám của PlantVillage không lấn át; đường đen là
  histogram tích lũy. Độ lệch chuẩn của L tăng nghĩa là độ tương phản tăng.
- Khử nhiễu: so trên cùng ảnh đã resize. Mép được xét là biên của mask vết bệnh chuẩn, ảnh không có
  vết bệnh (lá khỏe, virus) thì dùng biên lá. Ô phóng to đặt ở chỗ mép có cạnh mạnh nhất trên ảnh chưa lọc.
  Chỉ số tính trên kênh L bằng độ lớn gradient Sobel trung bình, sau lọc chia trước lọc:
  - giữ cạnh: trên dải mép, càng gần 100% càng giữ cạnh;
  - còn ở vùng phẳng: ở các điểm cách mép từ FLAT_DISTANCE_PX trở lên, càng thấp càng làm mịn (khử nhiễu) mạnh;
  - độ nổi cạnh = giữ cạnh / còn ở vùng phẳng: lớn hơn 1 nghĩa là sau lọc mép nổi rõ hơn so với vùng phẳng.
  Bộ lọc nào cũng làm giảm gradient ở mép một chút (vì nhiễu trên mép cũng bị lọc), nên chỉ số đáng so giữa
  hai bộ lọc là độ nổi cạnh.
"""
import argparse
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent
# Chạy bằng "python experiments/histogram_clahe.py" thì backend/ chưa có trong sys.path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from experiments import evaluate  # noqa: E402
from image_processing import pipeline, preprocessing  # noqa: E402

OUTPUT_DIR = BACKEND_DIR / 'experiments' / 'output'
CLAHE_DIR = OUTPUT_DIR / 'clahe'
DENOISE_DIR = OUTPUT_DIR / 'denoise'

ZOOM_SIZE = 96 # cạnh ô phóng to, tính trên ảnh 512x512
EDGE_BAND_PX = 1 # dải mép = biên mask nới ra EDGE_BAND_PX điểm mỗi phía
FLAT_DISTANCE_PX = 6 # vùng phẳng = cách mép từ chừng này điểm trở lên
STRONG_EDGE_PERCENT = 5 # không có mask: lấy 5% điểm có gradient lớn nhất làm mép
FIGURE_DPI = 120


def _rgb(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _lightness(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2LAB)[:, :, 0]


def _load_resized(image_path: Path) -> np.ndarray:
    return preprocessing.resize(pipeline.load_image(image_path))


def _save(fig, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=FIGURE_DPI, bbox_inches='tight')
    plt.close(fig)


def _plot_histogram(ax, lightness: np.ndarray, mask: np.ndarray | None, title: str, color: str) -> float:
    """Vẽ histogram kênh L (trong mask nếu có) kèm đường tích lũy. Trả về độ lệch chuẩn của L."""
    values = lightness[mask > 0] if mask is not None else lightness.ravel()
    hist = np.bincount(values, minlength=256)
    ax.bar(np.arange(256), hist, width=1.0, color=color)
    ax.set_xlim(0, 255)
    ax.set_xlabel('Độ sáng L (0–255)')
    ax.set_ylabel('Số điểm ảnh')
    ax.set_title(f'{title}\nTrung bình {values.mean():.0f}, độ lệch chuẩn {values.std():.1f}')
    cumulative = ax.twinx()
    cumulative.plot(np.cumsum(hist) / hist.sum(), color='black', linewidth=1)
    cumulative.set_ylim(0, 1.02)
    cumulative.set_ylabel('Tích lũy')
    return float(values.std())


def plot_clahe(image_path: Path, out_path: Path, leaf_mask: np.ndarray | None = None) -> tuple[float, float]:
    """Ảnh trước/sau CLAHE đặt cạnh nhau, bên dưới là histogram kênh L tương ứng.

    leaf_mask (512x512, 0/255): nếu có thì histogram chỉ tính trên vùng lá.
    Trả về (độ lệch chuẩn L trước, sau).
    """
    before = preprocessing.denoise(_load_resized(image_path))
    after = preprocessing.equalize(before)
    region = 'vùng lá' if leaf_mask is not None else 'cả ảnh'

    fig, axes = plt.subplots(
        2, 2, figsize=(11, 10), gridspec_kw={'height_ratios': (3, 2)}, layout='constrained',
    )
    axes[0, 0].imshow(_rgb(before))
    axes[0, 0].set_title('Trước CLAHE (đã resize, lọc Bilateral)')
    axes[0, 1].imshow(_rgb(after))
    axes[0, 1].set_title(
        f'Sau CLAHE (clipLimit={preprocessing.CLAHE_CLIP_LIMIT}, '
        f'lưới {preprocessing.CLAHE_TILE_GRID[0]}x{preprocessing.CLAHE_TILE_GRID[1]})'
    )
    for ax in axes[0]:
        ax.axis('off')
    std_before = _plot_histogram(axes[1, 0], _lightness(before), leaf_mask, f'Histogram L trước CLAHE ({region})',
                                 'tab:blue')
    std_after = _plot_histogram(axes[1, 1], _lightness(after), leaf_mask, f'Histogram L sau CLAHE ({region})',
                                'tab:orange')
    fig.suptitle(f'Cân bằng sáng CLAHE trên kênh L (CIELAB): {Path(image_path).parent.name}')
    _save(fig, out_path)
    return std_before, std_after


def _edge_band(boundary_mask: np.ndarray) -> np.ndarray:
    """Dải mép (bool) quanh biên của mask, rộng 2 * EDGE_BAND_PX + 1 điểm."""
    size = 2 * EDGE_BAND_PX + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (size, size))
    return cv2.morphologyEx(boundary_mask, cv2.MORPH_GRADIENT, kernel) > 0


def _gradient(lightness: np.ndarray) -> np.ndarray:
    gx = cv2.Sobel(lightness, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lightness, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def zoom_box(edge: np.ndarray, strength: np.ndarray, size: int = ZOOM_SIZE) -> tuple[int, int, int, int]:
    """Ô vuông cạnh size (x, y, w, h) nằm trong ảnh, chứa tổng strength trên dải mép lớn nhất."""
    height, width = edge.shape
    score = cv2.boxFilter(strength * edge, cv2.CV_32F, (size, size), normalize=False)
    cy, cx = np.unravel_index(int(np.argmax(score)), score.shape)
    x = int(np.clip(cx - size // 2, 0, width - size))
    y = int(np.clip(cy - size // 2, 0, height - size))
    return x, y, size, size


def edge_metrics(original: np.ndarray, filtered: np.ndarray, edge: np.ndarray) -> tuple[float, float, float]:
    """(giữ cạnh, còn ở vùng phẳng, độ nổi cạnh) của ảnh đã lọc so với ảnh gốc, định nghĩa ở đầu file.

    edge: dải mép (bool, cùng cỡ ảnh).
    """
    distance = cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 3)
    flat = distance >= FLAT_DISTANCE_PX
    before, after = _gradient(_lightness(original)), _gradient(_lightness(filtered))
    kept_edge = after[edge].mean() / before[edge].mean()
    kept_flat = after[flat].mean() / before[flat].mean()
    return float(kept_edge), float(kept_flat), float(kept_edge / kept_flat)


def compare_denoise(image_path: Path, out_path: Path, boundary_mask: np.ndarray | None = None,
                    boundary_name: str = 'vết bệnh') -> dict[str, tuple[float, float, float]]:
    """So sánh Bilateral với Median trên cùng một ảnh, phóng to một đoạn mép (vết bệnh hoặc lá).

    boundary_mask (512x512, 0/255): mask có biên là mép cần xem; không có thì xét cạnh mạnh nhất trên cả ảnh.
    Trả về {'bilateral': (giữ cạnh, còn ở vùng phẳng, độ nổi cạnh), 'median': (...)}.
    """
    original = _load_resized(image_path)
    filtered = {
        'bilateral': preprocessing.denoise(original),
        'median': cv2.medianBlur(original, preprocessing.MEDIAN_KSIZE),
    }
    strength = _gradient(_lightness(original))
    if boundary_mask is None or not boundary_mask.any():
        # Không có mask: coi STRONG_EDGE_PERCENT điểm có gradient lớn nhất là mép
        edge = strength >= np.percentile(strength, 100 - STRONG_EDGE_PERCENT)
        boundary_name = 'cạnh mạnh nhất'
    else:
        edge = _edge_band(boundary_mask)
    metrics = {name: edge_metrics(original, image, edge) for name, image in filtered.items()}
    x, y, w, h = zoom_box(edge, strength)

    titles = {
        'original': 'Ảnh sau resize, chưa lọc',
        'bilateral': (f'Bilateral (d={preprocessing.BILATERAL_D}, σ màu={preprocessing.BILATERAL_SIGMA_COLOR}, '
                      f'σ không gian={preprocessing.BILATERAL_SIGMA_SPACE})'),
        'median': f'Median ({preprocessing.MEDIAN_KSIZE}x{preprocessing.MEDIAN_KSIZE})',
    }
    images = {'original': original, **filtered}
    fig, axes = plt.subplots(2, 3, figsize=(15, 10.5), layout='constrained')
    for col, (name, image) in enumerate(images.items()):
        top, bottom = axes[0, col], axes[1, col]
        top.imshow(_rgb(image))
        top.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor='red', linewidth=2))
        top.set_title(titles[name], fontsize=10)
        bottom.imshow(_rgb(image[y:y + h, x:x + w]), interpolation='nearest')
        if name == 'original':
            bottom.set_title(f'Phóng to mép {boundary_name}')
        else:
            kept_edge, kept_flat, ratio = metrics[name]
            bottom.set_title(f'Mép còn {kept_edge:.0%}, vùng phẳng còn {kept_flat:.0%}\nĐộ nổi cạnh {ratio:.2f}')
        for ax in (top, bottom):
            ax.axis('off')
    fig.suptitle(f'Khử nhiễu Bilateral và Median: {Path(image_path).parent.name}')
    _save(fig, out_path)
    return metrics


def first_per_class(items: list) -> list:
    """Ảnh đầu tiên của mỗi lớp, giữ thứ tự xuất hiện trong danh sách."""
    seen = {}
    for item in items:
        seen.setdefault(item.disease, item)
    return list(seen.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Vẽ histogram trước/sau CLAHE và so sánh Bilateral với Median.')
    parser.add_argument('--list', type=Path, default=evaluate.GROUND_TRUTH_FILE, help='file danh sách ảnh chuẩn')
    parser.add_argument('--masks', type=Path, default=evaluate.MASKS_DIR, help='thư mục chứa leaf/ và lesion/')
    parser.add_argument('--out', type=Path, default=OUTPUT_DIR, help='thư mục lưu clahe/ và denoise/')
    args = parser.parse_args(argv)

    rows = []
    for index, item in enumerate(first_per_class(evaluate.load_ground_truth(args.list, args.masks)), start=1):
        name = f'{index:02d}_{item.disease.removeprefix(evaluate.CLASS_PREFIX)}.png'
        std_before, std_after = plot_clahe(item.path, args.out / 'clahe' / name, item.leaf_mask)
        has_lesion = item.lesion_mask.any()
        metrics = compare_denoise(
            item.path, args.out / 'denoise' / name,
            item.lesion_mask if has_lesion else item.leaf_mask,
            'vết bệnh' if has_lesion else 'lá',
        )
        rows.append((item, has_lesion, std_before, std_after, metrics))
        print(f'{item.path.name} -> {name}')

    print(f'\nĐã lưu {len(rows)} hình vào {args.out / "clahe"} và {args.out / "denoise"}\n')
    print('| Lớp | Mép xét | Độ lệch chuẩn L trước → sau CLAHE | Mép còn (Bilateral / Median) '
          '| Vùng phẳng còn (Bilateral / Median) | Độ nổi cạnh (Bilateral / Median) |')
    print('|---|---|---:|---:|---:|---:|')
    for item, has_lesion, std_before, std_after, metrics in rows:
        bilateral, median = metrics['bilateral'], metrics['median']
        print(f'| {item.disease.removeprefix(evaluate.CLASS_PREFIX)} | {"vết bệnh" if has_lesion else "lá"} '
              f'| {std_before:.1f} → {std_after:.1f} | {bilateral[0]:.0%} / {median[0]:.0%} '
              f'| {bilateral[1]:.0%} / {median[1]:.0%} | {bilateral[2]:.2f} / {median[2]:.2f} |')
    ratios = {name: np.mean([row[4][name][2] for row in rows]) for name in ('bilateral', 'median')}
    wins = sum(row[4]['bilateral'][2] > row[4]['median'][2] for row in rows)
    print(f'\nĐộ nổi cạnh trung bình: Bilateral {ratios["bilateral"]:.2f}, Median {ratios["median"]:.2f}; '
          f'Bilateral cao hơn ở {wins}/{len(rows)} ảnh.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
