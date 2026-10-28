"""Tạo ảnh rà soát phân đoạn lá và đốm bệnh mà không chạy phân loại."""
import argparse
from pathlib import Path

import cv2
import numpy as np

from image_processing import pipeline, preprocessing, segmentation, steps

IMAGE_EXTENSIONS = {'.bmp', '.jpeg', '.jpg', '.png', '.tif', '.tiff', '.webp'}
TILE_SIZE = (512, 512)
HEADER_HEIGHT = 36
PANEL_COLUMNS = 3
PANEL_ROWS = 2


def _collect_images(inputs: list[Path]) -> list[Path]:
    images: list[Path] = []
    for path in inputs:
        if not path.exists():
            raise FileNotFoundError(f'Không tìm thấy đường dẫn: {path}')
        if path.is_file():
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                candidates = [path]
            elif path.suffix.lower() == '.txt':
                dataset_root = path.parent.parent
                candidates = []
                for line_number, line in enumerate(
                    path.read_text(encoding='utf-8').splitlines(), start=1,
                ):
                    relative_path = line.strip()
                    if not relative_path:
                        continue
                    image_path = dataset_root / Path(relative_path)
                    if not image_path.is_file():
                        raise FileNotFoundError(
                            f'Ảnh trong danh sách không tồn tại '
                            f'(dòng {line_number} của {path}): {image_path}'
                        )
                    if image_path.suffix.lower() in IMAGE_EXTENSIONS:
                        candidates.append(image_path)
            else:
                candidates = []
        else:
            candidates = sorted(
                item for item in path.rglob('*')
                if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
            )
        images.extend(candidates)
    return list(dict.fromkeys(images))


def _tile(image: np.ndarray, title: str) -> np.ndarray:
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    resized = cv2.resize(image, TILE_SIZE, interpolation=cv2.INTER_AREA)
    tile = np.zeros(
        (TILE_SIZE[1] + HEADER_HEIGHT, TILE_SIZE[0], 3), dtype=np.uint8,
    )
    tile[HEADER_HEIGHT:] = resized
    cv2.putText(
        tile, title, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
        (255, 255, 255), 1, cv2.LINE_AA,
    )
    return tile


def _make_panel(
    original: np.ndarray,
    resized: np.ndarray,
    processed: np.ndarray,
    leaf_mask: np.ndarray,
    lesion_mask: np.ndarray,
    infected_ratio: float,
) -> np.ndarray:
    leaf_overlay = resized.copy()
    leaf_pixels = leaf_mask > 0
    leaf_overlay[leaf_pixels] = (
        0.55 * leaf_overlay[leaf_pixels]
        + 0.45 * np.array((0, 220, 0), dtype=np.float32)
    ).astype(np.uint8)

    lesion_overlay = leaf_overlay.copy()
    lesion_pixels = lesion_mask > 0
    lesion_overlay[lesion_pixels] = (
        0.45 * lesion_overlay[lesion_pixels]
        + 0.55 * np.array((0, 0, 255), dtype=np.float32)
    ).astype(np.uint8)

    # Tiêu đề viết không dấu: font Hershey của cv2.putText chỉ vẽ được ký tự ASCII
    tiles = [
        _tile(original, 'Anh goc'),
        _tile(processed, 'Sau tien xu ly (CLAHE)'),
        _tile(leaf_mask, 'Mask la'),
        _tile(leaf_overlay, 'Lop phu la (xanh)'),
        _tile(lesion_mask, 'Mask dom benh'),
        _tile(lesion_overlay, f'Dom benh (do) - nhiem {infected_ratio:.2%}'),
    ]
    rows = [
        cv2.hconcat(tiles[index:index + PANEL_COLUMNS])
        for index in range(0, PANEL_COLUMNS * PANEL_ROWS, PANEL_COLUMNS)
    ]
    return cv2.vconcat(rows)


def review_image(
    path: Path, output_path: Path,
) -> tuple[int, int, float, np.ndarray]:
    original = pipeline.load_image(path)
    processed, preprocessed_steps = preprocessing.preprocess(original)
    leaf_mask, _ = segmentation.segment_leaf(processed)
    lesion_mask, _ = segmentation.segment_lesions(processed, leaf_mask)

    leaf_area = cv2.countNonZero(leaf_mask)
    lesion_area = cv2.countNonZero(lesion_mask)
    infected_ratio = lesion_area / leaf_area if leaf_area else 0.0
    panel = _make_panel(
        original,
        preprocessed_steps[steps.RESIZED],
        processed,
        leaf_mask,
        lesion_mask,
        infected_ratio,
    )
    success, encoded = cv2.imencode('.png', panel)
    if not success:
        raise OSError(f'Không lưu được ảnh kết quả: {output_path}')
    encoded.tofile(str(output_path))
    return leaf_area, lesion_area, infected_ratio, panel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Xem trực quan segmentation lá/đốm bệnh, không chạy classifier.',
    )
    parser.add_argument(
        'inputs', nargs='+', type=Path,
        help='đường dẫn ảnh, thư mục ảnh, hoặc file split .txt',
    )
    parser.add_argument(
        '--out', type=Path, default=Path('experiments/output/segmentation-review'),
        help='thư mục lưu panel kết quả',
    )
    parser.add_argument(
        '--show', action='store_true',
        help='mở từng panel bằng cửa sổ OpenCV; nhấn phím bất kỳ để tiếp tục, Esc để dừng',
    )
    args = parser.parse_args(argv)

    images = _collect_images(args.inputs)
    if not images:
        parser.error('Không tìm thấy ảnh có định dạng hỗ trợ trong đường dẫn đã cho.')
    args.out.mkdir(parents=True, exist_ok=True)

    for index, image_path in enumerate(images, start=1):
        output_path = args.out / f'{index:03d}_{image_path.stem}_segmentation.png'
        leaf_area, lesion_area, infected_ratio, panel = review_image(
            image_path, output_path,
        )
        print(
            f'{image_path} -> {output_path} | '
            f'leaf={leaf_area}px lesion={lesion_area}px '
            f'infected={infected_ratio:.2%}'
        )
        if args.show:
            cv2.imshow('Segmentation review', panel)
            key = cv2.waitKey(0)
            if key == 27:
                break

    if args.show:
        cv2.destroyAllWindows()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
