"""Vẽ các giai đoạn morphology và đối chiếu mask vết bệnh chuẩn.

Chạy từ backend/:
    python experiments/visualize_morphology.py

Hình được lưu trong experiments/output/morphology/.
"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from experiments import evaluate  # noqa: E402
from image_processing import pipeline, preprocessing, segmentation, steps  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / 'output' / 'morphology'
FIGURE_DPI = 120


@dataclass
class Example:
    item: evaluate.GroundTruth
    image: np.ndarray
    lesion_mask: np.ndarray
    metrics: dict


def _validate_inputs(
    image: np.ndarray,
    leaf_mask: np.ndarray,
    lesion_raw: np.ndarray,
    lesion_mask: np.ndarray,
) -> None:
    if (
        not isinstance(image, np.ndarray)
        or image.dtype != np.uint8
        or image.ndim != 3
        or image.shape[2] != 3
    ):
        raise ValueError('image phải là ảnh BGR uint8 có shape (H, W, 3)')
    for name, mask in (
        ('leaf_mask', leaf_mask),
        ('lesion_raw', lesion_raw),
        ('lesion_mask', lesion_mask),
    ):
        if (
            not isinstance(mask, np.ndarray)
            or mask.dtype != np.uint8
            or mask.shape != image.shape[:2]
        ):
            raise ValueError(f'{name} phải là mask uint8 cùng kích thước image')
        if not np.isin(mask, (0, 255)).all():
            raise ValueError(f'{name} chỉ được chứa giá trị 0 và 255')


def _mask_rgb(mask: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)


def _ksize(size: tuple[int, int]) -> str:
    return f'{size[0]}×{size[1]}'


def _leaf_segmentation_stages(image: np.ndarray) -> tuple[np.ndarray, ...]:
    """Chạy lại đúng các bước tạo mask của segment_leaf để vẽ minh họa."""
    cv2.setRNGSeed(pipeline.RNG_SEED)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    green_seed = cv2.inRange(
        hsv,
        np.array(segmentation.LEAF_GREEN_LOWER, dtype=np.uint8),
        np.array(segmentation.LEAF_GREEN_UPPER, dtype=np.uint8),
    )
    grabcut_mask = segmentation._refine_leaf_mask(image, hsv, green_seed)
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, segmentation.LEAF_CLOSE_KSIZE,
    )
    closed_mask = cv2.morphologyEx(
        grabcut_mask, cv2.MORPH_CLOSE, close_kernel,
    )
    filled_mask = segmentation._fill_largest_contour(closed_mask)
    return green_seed, grabcut_mask, closed_mask, filled_mask


def plot_morphology(
    image: np.ndarray,
    leaf_mask: np.ndarray,
    lesion_raw: np.ndarray,
    lesion_mask: np.ndarray,
    output_path: Path,
    title: str = '',
) -> None:
    """Lưu các mask trước/sau morphology và contour do pipeline tạo."""
    _validate_inputs(image, leaf_mask, lesion_raw, lesion_mask)
    leaf_seed, leaf_grabcut, leaf_closed, leaf_filled = (
        _leaf_segmentation_stages(image)
    )
    if not np.array_equal(leaf_filled, leaf_mask):
        raise ValueError('Các bước minh họa không khớp mask do segment_leaf tạo')

    # Chạy lại phần hình thái học của segment_lesions: đổi segment_lesions thì phải sửa chỗ này theo
    open_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, segmentation.LESION_OPEN_KSIZE,
    )
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, segmentation.LESION_CLOSE_KSIZE,
    )
    lesion_opened = cv2.morphologyEx(lesion_raw, cv2.MORPH_OPEN, open_kernel)
    lesion_open_close = cv2.morphologyEx(
        lesion_opened, cv2.MORPH_CLOSE, close_kernel,
    )
    edge_size = segmentation.LESION_EDGE_MARGIN_PX * 2 + 1
    leaf_core = cv2.erode(leaf_mask, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (edge_size, edge_size),
    ))
    lesion_in_core = cv2.bitwise_and(lesion_open_close, leaf_core)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(lesion_in_core, connectivity=8)
    lesion_filtered = np.zeros_like(lesion_in_core)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] >= segmentation.LESION_MIN_AREA_PX:
            lesion_filtered[labels == label] = 255
    if not np.array_equal(lesion_filtered, lesion_mask):
        raise ValueError('Các bước minh họa không khớp mask do segment_lesions tạo')
    contour_image = segmentation.draw_lesions(image, lesion_mask)

    panels = [
        (cv2.cvtColor(image, cv2.COLOR_BGR2RGB), 'Ảnh sau tiền xử lý'),
        (_mask_rgb(leaf_seed), 'Seed xanh HSV'),
        (_mask_rgb(leaf_grabcut), 'Sau GrabCut + khôi phục mép màu ấm'),
        (_mask_rgb(leaf_closed), f'Sau Closing lá {_ksize(segmentation.LEAF_CLOSE_KSIZE)}'),
        (_mask_rgb(leaf_filled), 'Mask lá sau tô contour'),
        (_mask_rgb(lesion_raw), 'Mask bệnh thô'),
        (_mask_rgb(lesion_opened), f'Sau Opening {_ksize(segmentation.LESION_OPEN_KSIZE)}'),
        (_mask_rgb(lesion_open_close), f'Sau Closing {_ksize(segmentation.LESION_CLOSE_KSIZE)}'),
        (
            _mask_rgb(lesion_mask),
            f'Sau giao leaf_core + lọc thành phần ≥{segmentation.LESION_MIN_AREA_PX} px',
        ),
        (
            cv2.cvtColor(contour_image, cv2.COLOR_BGR2RGB),
            'Contour bệnh cuối',
        ),
    ]

    figure, axes = plt.subplots(2, 5, figsize=(18, 8), constrained_layout=True)
    for ax, (panel, panel_title) in zip(axes.flat, panels):
        ax.imshow(panel, cmap='gray' if panel.ndim == 2 else None, vmin=0, vmax=255)
        ax.set_title(panel_title)
        ax.axis('off')
    figure.suptitle(
        f'{title or "Giai đoạn morphology"}\n'
        'Mask lá theo đúng seed → GrabCut → Closing → tô contour của segment_leaf.',
        fontsize=12,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches='tight')
    plt.close(figure)


def _examples_overlay(
    image: np.ndarray, truth: np.ndarray, prediction: np.ndarray,
) -> np.ndarray:
    comparison = evaluate.color_comparison(image, prediction, truth)
    return cv2.cvtColor(comparison, cv2.COLOR_BGR2RGB)


def _select_examples(
    examples: list[Example],
) -> list[tuple[str, Example]]:
    positive = [
        example for example in examples
        if cv2.countNonZero(example.item.lesion_mask) > 0
    ]
    negative = [
        example for example in examples
        if cv2.countNonZero(example.item.lesion_mask) == 0
    ]
    selected: list[tuple[str, Example]] = []
    if positive:
        selected.extend([
            ('IoU cao nhất', max(
                positive, key=lambda case: case.metrics['iou_vet_benh'],
            )),
            ('IoU thấp nhất', min(
                positive, key=lambda case: case.metrics['iou_vet_benh'],
            )),
        ])
    false_positives = [
        case for case in negative
        if cv2.countNonZero(case.lesion_mask) > 0
    ]
    true_negatives = [
        case for case in negative
        if cv2.countNonZero(case.lesion_mask) == 0
    ]
    if false_positives:
        # Lấy ảnh báo nhầm nhiều pixel nhất để hình thấy rõ lỗi
        selected.append(('Báo nhầm (mask chuẩn rỗng)', max(
            false_positives, key=lambda case: cv2.countNonZero(case.lesion_mask),
        )))
    if true_negatives:
        selected.append(('Đúng âm (mask chuẩn rỗng)', true_negatives[0]))
    if not selected:
        raise ValueError('Không có ví dụ để vẽ từ danh sách mask chuẩn')
    return selected


def plot_examples(examples: list[Example], output_path: Path) -> None:
    """Lưu ví dụ IoU tốt/xấu, báo nhầm và đúng âm theo mask chuẩn."""
    selected = _select_examples(examples)

    figure, axes = plt.subplots(
        len(selected), 4, figsize=(15, 3.8 * len(selected)),
        squeeze=False, constrained_layout=True,
    )
    columns = ('Ảnh', 'Mask chuẩn', 'Mask dự đoán', 'So sánh: đúng / thiếu / thừa')
    for row_index, (label, example) in enumerate(selected):
        panels = (
            cv2.cvtColor(example.image, cv2.COLOR_BGR2RGB),
            _mask_rgb(example.item.lesion_mask),
            _mask_rgb(example.lesion_mask),
            _examples_overlay(
                example.image, example.item.lesion_mask, example.lesion_mask,
            ),
        )
        iou_value = example.metrics['iou_vet_benh']
        iou_text = 'n/a' if iou_value is None else f'{iou_value:.3f}'
        for column, (ax, panel) in enumerate(zip(axes[row_index], panels)):
            ax.imshow(panel, cmap='gray' if panel.ndim == 2 else None)
            if column == 0:
                ax.set_title(
                    f'{label} | {example.item.disease.removeprefix(evaluate.CLASS_PREFIX)} '
                    f'| IoU={iou_text}\n{columns[column]}',
                )
            else:
                ax.set_title(columns[column])
            ax.axis('off')
    figure.suptitle(
        'So sánh mask (xanh lá: đúng, đỏ: báo nhầm, xanh dương: bỏ sót)',
        fontsize=14,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches='tight')
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(
        description='Vẽ morphology và ví dụ dự đoán đúng/sai so với mask chuẩn.',
    )
    parser.add_argument(
        '--list', type=Path, default=evaluate.GROUND_TRUTH_FILE,
        help='file danh sách ảnh chuẩn',
    )
    parser.add_argument(
        '--masks', type=Path, default=evaluate.MASKS_DIR,
        help='thư mục chứa leaf/ và lesion/',
    )
    parser.add_argument(
        '--out', type=Path, default=OUTPUT_DIR,
        help='thư mục lưu ảnh PNG',
    )
    args = parser.parse_args(argv)
    items = evaluate.load_ground_truth(args.list, args.masks)
    if not items:
        parser.error('Danh sách mask chuẩn không có ảnh.')

    args.out.mkdir(parents=True, exist_ok=True)
    examples = []
    for index, item in enumerate(items, start=1):
        image = pipeline.load_image(item.path)
        processed, _ = preprocessing.preprocess(image)
        cv2.setRNGSeed(pipeline.RNG_SEED)
        leaf_mask, _ = segmentation.segment_leaf(processed)
        lesion_mask, intermediates = segmentation.segment_lesions(
            processed, leaf_mask,
        )
        metrics = evaluate.evaluate_image(
            item.leaf_mask, item.lesion_mask, leaf_mask, lesion_mask,
        )
        output_path = args.out / f'{index:02d}_{item.path.stem}_morphology.png'
        plot_morphology(
            processed, leaf_mask, intermediates[steps.LESION_MASK_RAW],
            lesion_mask, output_path,
            f'{item.disease.removeprefix(evaluate.CLASS_PREFIX)} — {item.path.name}',
        )
        examples.append(Example(item, processed, lesion_mask, metrics))
        print(f'{item.path.name} -> {output_path}')

    example_path = args.out / 'examples_correct_vs_wrong.png'
    plot_examples(examples, example_path)
    print(f'Ví dụ đúng/sai -> {example_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
