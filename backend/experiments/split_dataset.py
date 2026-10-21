"""Chia ảnh PlantVillage thành tập train/test theo từng lớp. Phụ trách: Thành viên 1.

Ảnh đặt ở backend/dataset/plantvillage/<tên lớp>/. Tên thư mục phải trùng diseases.code (tên gốc
PlantVillage raw/color), vì model học nhãn từ tên thư mục. Một số bản PlantVillage trên mạng đã đổi tên
2 thư mục, cần đổi lại trước khi chạy:
    Tomato___Spider_mites_Two_spotted_spider_mite -> Tomato___Spider_mites Two-spotted_spider_mite
    Tomato___Tomato_YellowLeaf__Curl_Virus        -> Tomato___Tomato_Yellow_Leaf_Curl_Virus

Chạy từ thư mục backend/:
    python experiments/split_dataset.py
Kết quả ghi vào backend/dataset/splits/train.txt và test.txt: mỗi dòng là đường dẫn tương đối
tính từ backend/dataset/, dùng dấu /, ví dụ plantvillage/Tomato___healthy/abc.JPG.
Lớp của một ảnh là tên thư mục cha của nó.

Đọc file split bằng read_text(encoding='utf-8').splitlines(), không dùng split(): gần như mọi tên file
và một tên thư mục có dấu cách.

Kết quả chia phụ thuộc phiên bản scikit-learn (đang ghim trong requirements.txt). Không chạy lại script
sau khi nâng phiên bản, nếu không cả nhóm sẽ dùng bộ train/test khác với bộ đã commit.
"""
from pathlib import Path

from sklearn.model_selection import train_test_split

DATASET_DIR = Path(__file__).resolve().parent.parent / 'dataset'
PLANTVILLAGE_DIR = DATASET_DIR / 'plantvillage'
SPLITS_DIR = DATASET_DIR / 'splits'

TEST_SIZE = 0.2
SEED = 42
# So sánh đuôi file không phân biệt hoa thường: PlantVillage có cả .jpg, .JPG và một ảnh .jpeg
IMAGE_EXTENSIONS = ('.jpg', '.jpeg')


def list_images(root: Path) -> list[Path]:
    """Mọi ảnh trong các thư mục lớp con của root, sắp xếp theo đường dẫn.

    Bỏ qua file khác đuôi ảnh (file nén, file rác như svn-r6Yb5c). Sắp xếp theo chuỗi as_posix()
    thay vì so sánh Path, vì Path trên Windows so sánh không phân biệt hoa thường còn trên Linux thì có:
    danh sách phải giống nhau trên mọi máy để chia lại ra đúng kết quả cũ.
    """
    images = [
        path for path in root.glob('*/*')
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda path: path.as_posix())


def split_dataset(root: Path = PLANTVILLAGE_DIR, test_size: float = TEST_SIZE,
                  seed: int = SEED) -> tuple[list[Path], list[Path]]:
    """Chia ảnh trong root thành (train, test), giữ nguyên tỉ lệ từng lớp (stratify theo tên thư mục).

    Cùng dữ liệu, test_size và seed thì luôn ra cùng kết quả. Hai danh sách trả về đã sắp xếp.
    """
    images = list_images(Path(root))
    if not images:
        raise ValueError(f'Không tìm thấy ảnh nào trong {root}')
    labels = [path.parent.name for path in images]

    train, test = train_test_split(images, test_size=test_size, random_state=seed, stratify=labels)
    return sorted(train, key=lambda path: path.as_posix()), sorted(test, key=lambda path: path.as_posix())


def write_split(paths: list[Path], out_file: Path) -> None:
    """Ghi mỗi ảnh một dòng, đường dẫn tương đối tính từ DATASET_DIR, dùng dấu /."""
    lines = [path.relative_to(DATASET_DIR).as_posix() for path in paths]
    # newline='\n' để file giống hệt nhau trên Windows và Linux
    with open(out_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def count_by_class(paths: list[Path]) -> dict[str, int]:
    counts = {}
    for path in paths:
        counts[path.parent.name] = counts.get(path.parent.name, 0) + 1
    return counts


def main():
    train, test = split_dataset()
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    write_split(train, SPLITS_DIR / 'train.txt')
    write_split(test, SPLITS_DIR / 'test.txt')

    # Bảng số ảnh từng lớp, dạng Markdown để dán thẳng vào mô tả PR
    train_counts, test_counts = count_by_class(train), count_by_class(test)
    print('| Lớp | Train | Test | Tổng |')
    print('|---|---:|---:|---:|')
    for name in sorted(train_counts.keys() | test_counts.keys()):
        n_train, n_test = train_counts.get(name, 0), test_counts.get(name, 0)
        print(f'| `{name}` | {n_train} | {n_test} | {n_train + n_test} |')
    print(f'| **Tổng** | **{len(train)}** | **{len(test)}** | **{len(train) + len(test)}** |')


if __name__ == '__main__':
    main()
