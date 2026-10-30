"""Ghép 5 giai đoạn thành một lần chẩn đoán. Phụ trách: Thành viên 4.

Chạy thử một ảnh (từ thư mục backend/):
    python -m image_processing.pipeline duong/dan/anh.jpg --out ket_qua/
"""
import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import classifier, preprocessing, segmentation, severity, steps
from .errors import PipelineError

# GrabCut khởi tạo ngẫu nhiên: cố định seed để cùng một ảnh luôn ra cùng một mask, giống lúc huấn luyện
RNG_SEED = 0


@dataclass
class PipelineResult:
    # Các trường khớp một-một với cột kết quả của diagnosis_histories
    disease_code: str # diseases.code
    disease_confidence: float # [0, 1]
    severity_level: int # 0–4
    leaf_area_px: int
    lesion_area_px: int
    infected_ratio: float # [0, 1], làm tròn 4 chữ số như cột decimal(5,4)
    lesion_count: int
    lesions: list[dict]
    processed_image: np.ndarray = field(repr=False) # ảnh vẽ contours
    steps: dict[str, np.ndarray] = field(repr=False) # theo thứ tự steps.ORDER

    @property
    def recommendation(self) -> str:
        return severity.IPM_RECOMMENDATIONS[self.severity_level]


def load_image(path) -> np.ndarray:
    # cv2.imread trả None với đường dẫn có dấu tiếng Việt trên Windows -> đọc byte rồi giải mã
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
    if image is None:
        raise PipelineError('Không đọc được ảnh. Hãy tải lên ảnh JPG hoặc PNG.')
    return image


def _check_mask(mask, image, name):
    if mask.dtype != np.uint8 or mask.shape != image.shape[:2]:
        raise ValueError(f'{name} phải là uint8 kích thước {image.shape[:2]}, nhận {mask.dtype} {mask.shape}')
    if not np.isin(mask, (0, 255)).all():
        raise ValueError(f'{name} chỉ được chứa giá trị 0 và 255')


def run(image: np.ndarray) -> PipelineResult:
    """Chẩn đoán một ảnh lá BGR. Ném PipelineError khi ảnh không chẩn đoán được."""
    # RNG của OpenCV riêng cho từng luồng nên đặt ở đây vẫn đúng khi nhiều request chạy cùng lúc
    cv2.setRNGSeed(RNG_SEED)
    processed, pre_steps = preprocessing.preprocess(image)

    leaf_mask, leaf_steps = segmentation.segment_leaf(processed)
    _check_mask(leaf_mask, processed, 'leaf_mask')
    leaf_area = cv2.countNonZero(leaf_mask)
    if leaf_area == 0:
        raise PipelineError('Không tìm thấy lá trong ảnh. Hãy chụp một chiếc lá trên nền đơn sắc.')

    lesion_mask, lesion_steps = segmentation.segment_lesions(processed, leaf_mask)
    _check_mask(lesion_mask, processed, 'lesion_mask')
    if cv2.countNonZero(cv2.bitwise_and(lesion_mask, cv2.bitwise_not(leaf_mask))):
        raise ValueError('lesion_mask có điểm nằm ngoài leaf_mask')
    lesion_area = cv2.countNonZero(lesion_mask)
    lesions = segmentation.measure_lesions(lesion_mask)

    disease_code, confidence = classifier.predict(classifier.extract_features(processed, leaf_mask))

    all_steps = {**pre_steps, **leaf_steps, **lesion_steps}
    if set(all_steps) != set(steps.ORDER):
        raise ValueError(f'Ảnh trung gian phải đủ các bước {steps.ORDER}, nhận {tuple(all_steps)}')

    return PipelineResult(
        disease_code=disease_code,
        disease_confidence=round(confidence, 4),
        severity_level=severity.severity_level(lesion_area, leaf_area),
        leaf_area_px=leaf_area,
        lesion_area_px=lesion_area,
        infected_ratio=round(lesion_area / leaf_area, 4),
        lesion_count=len(lesions),
        lesions=lesions,
        processed_image=segmentation.draw_lesions(processed, lesion_mask),
        steps={name: all_steps[name] for name in steps.ORDER},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description='Chạy pipeline trên một ảnh lá cà chua.')
    parser.add_argument('image', type=Path)
    parser.add_argument('--out', type=Path, help='thư mục lưu ảnh từng bước và ảnh kết quả')
    args = parser.parse_args(argv)

    result = run(load_image(args.image))
    summary = {k: v for k, v in asdict(result).items() if k not in ('processed_image', 'steps')}
    summary['recommendation'] = result.recommendation
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        images = {**result.steps, 'result': result.processed_image}
        for index, (name, img) in enumerate(images.items(), start=1):
            _, buffer = cv2.imencode('.png', img)
            buffer.tofile(str(args.out / f'{index:02d}_{name}.png'))


if __name__ == '__main__':
    main()
