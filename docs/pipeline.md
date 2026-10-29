# Pipeline xử lý ảnh — quy ước vào/ra giữa các module

Tài liệu này là "hợp đồng" giữa các module trong `backend/image_processing/`. Mỗi người viết module của mình độc lập, miễn là đúng kiểu dữ liệu vào/ra ở đây; `pipeline.py` ghép các module lại và kiểm tra quy ước mỗi lần chạy. Phạm vi và tham số thuật toán: [TongQuanDuAn.md](TongQuanDuAn.md).

## 1. Phân công theo file

| File | Giai đoạn | Phụ trách | Trạng thái |
|---|---|---|---|
| `preprocessing.py` | 1. Tiền xử lý: resize, khử nhiễu, CLAHE | Thành viên 1 | Xong |
| `segmentation.py` | 2. Tách lá khỏi nền · 3. Tách đốm bệnh, đo từng đốm, vẽ contours | Thành viên 2 | Xong bản đầu, ngưỡng đốm bệnh còn tạm thời |
| `classifier.py` | 4. Đặc trưng GLCM + Color Moments, phân loại tên bệnh | Thành viên 3 | Khung — cần cài đặt `extract_features` và huấn luyện model |
| `severity.py` | 5. Cấp độ 0–4 và khuyến nghị IPM | Thành viên 4 | Xong |
| `pipeline.py` | Ghép 5 giai đoạn, kiểm tra quy ước, chạy thử từ dòng lệnh | Thành viên 4 | Xong |
| `steps.py` | Tên các ảnh trung gian | — | Xong |

Hàm chưa cài đặt ném `NotImplementedError` kèm tên người phụ trách. Docstring của từng hàm ghi rõ cần làm gì.

## 2. Kiểu dữ liệu chung

| Loại | Kiểu | Ghi chú |
|---|---|---|
| Ảnh màu | `np.ndarray` `uint8`, shape `(H, W, 3)`, thứ tự kênh **BGR** | Thứ tự của OpenCV. Đổi màu dùng `cv2.COLOR_BGR2HSV`, `cv2.COLOR_BGR2LAB` |
| Ảnh sau tiền xử lý | Ảnh màu `(512, 512, 3)` | `TARGET_SIZE` trong `preprocessing.py` |
| Mask | `np.ndarray` `uint8`, shape `(H, W)` bằng ảnh, **chỉ gồm 0 và 255** | 255 = vùng được chọn. Không dùng `bool` hay 0/1 |
| Ảnh trung gian | `dict[str, np.ndarray]`, khóa là hằng số trong `steps.py` | Ảnh màu hoặc ảnh xám đều được |

Kênh H của HSV trong OpenCV chạy **0–179** (không phải 0–359).

## 3. Chữ ký từng hàm

```python
# preprocessing.py — Thành viên 1
preprocess(image) -> (processed, {RESIZED, DENOISED, CLAHE})   # đã ghép sẵn 3 hàm dưới
resize(image) -> image                # (512, 512, 3)
denoise(image) -> image               # bilateralFilter(d=9, 75, 75) hoặc medianBlur(5)
equalize(image) -> image              # BGR -> LAB, CLAHE(clipLimit=2.0, 8x8) trên L, LAB -> BGR

# segmentation.py — Thành viên 2
segment_leaf(image) -> (leaf_mask, {SATURATION, LEAF_MASK})
segment_lesions(image, leaf_mask) -> (lesion_mask, {ROI, HEALTHY_MASK, LESION_MASK_RAW, LESION_MASK})
measure_lesions(lesion_mask) -> [{"area", "perimeter", "circularity", "center": [x, y], "bbox": [x, y, w, h]}, ...]
draw_lesions(image, lesion_mask) -> image   # viền đỏ quanh từng đốm
process_image(preprocessed_img, original_img=None) -> dict  # kết quả segmentation độc lập

# classifier.py — Thành viên 3
extract_features(image, leaf_mask) -> np.ndarray   # vector 1 chiều, cùng thứ tự với lúc huấn luyện
predict(features) -> (disease_code, confidence)    # đã viết sẵn, dùng model tại MODEL_PATH
```

`image` truyền vào giai đoạn 2, 3, 4 là ảnh **đã tiền xử lý**.

`process_image` là giao diện tiện ích độc lập, dùng cùng tên trường và đơn vị
với `pipeline.run()`. Dict trả về gồm `mask_leaf`, `mask_healthy`,
`mask_lesion`, `processed_image`, `leaf_area_px`, `lesion_area_px` và
`infected_ratio`. Hai diện tích là số pixel mask; `infected_ratio` là tỷ lệ
0–1. Không tìm thấy lá thì hàm ném `PipelineError`, tương tự việc pipeline báo
lỗi ảnh không chẩn đoán được. Nếu truyền `original_img` có kích thước khác,
`process_image` resize mask bằng nearest-neighbor trước khi gọi `draw_lesions`;
hàm vẽ không tự thay đổi kích thước mask.

## 4. Quy tắc pipeline kiểm tra

`pipeline.run()` ném lỗi ngay khi một module trả sai quy ước, để phát hiện sớm khi ghép:

| Kiểm tra | Lỗi |
|---|---|
| Mask đúng `uint8`, đúng kích thước, chỉ có 0/255 | `ValueError` |
| `leaf_mask` không rỗng | `PipelineError` — ảnh không có lá, báo cho người dùng |
| `lesion_mask` nằm trọn trong `leaf_mask` | `ValueError` |
| Đủ 9 ảnh trung gian theo `steps.ORDER` | `ValueError` |

`PipelineError` là lỗi do **ảnh** (người dùng gửi ảnh không phải lá, ảnh hỏng…): thông báo tiếng Việt, lưu vào `diagnosis_histories.error_message`. `ValueError` / `NotImplementedError` là lỗi do **code**.

**Leaf mask phải gồm cả vùng vết bệnh.** Segmentation chuyển ảnh BGR sang
HSV và dùng ngưỡng xanh bão hòa cao (H 25–95, S 40–255, V 30–255) làm
foreground seed. GrabCut phân loại vùng lân cận theo màu ảnh và nền cục bộ,
để phục hồi nếp gập tối, mô hoại tử và cuống có màu yếu mà không mở rộng mask
vào vùng bóng ngoại cảnh. Pixel trung tính và pixel Hue nâu/đỏ được đánh dấu
nền có khả năng; chỉ pixel hoại tử bão hòa cao, Hue 15–24 hoặc 165–179 và
cách seed tối đa 20 pixel mới được khôi phục sau phân đoạn. Sau đó chỉ closing
hình thái bằng kernel elip 5×5 chạy một lần, không opening/erosion, nhằm tránh
làm đứt cuống. Contour ngoài lớn nhất cùng các contour có diện tích ít nhất 3%
diện tích contour lớn nhất được tô kín. Tách mô khỏe xét đồng thời Hue,
Saturation và Value; mô trung tính ít bão hòa không bị tính thành đốm. Khi
tách đốm, vùng cách biên `leaf_mask` tối đa 5 pixel cũng bị loại để hạn chế
bóng đổ sát mép lá bị nhận nhầm là bệnh.
Opening, closing và ngưỡng diện tích thành phần tối thiểu trong bước tách đốm
loại nhiễu nhỏ. `lesion_mask` luôn là tập con của `leaf_mask`.

*Ghi chú:* Ngưỡng Hue/Saturation/Value đốm bệnh được lựa chọn trên tập huấn
luyện (train) theo tiêu chí tối ưu tỷ lệ lá khỏe bị xếp cấp >= 2 thấp nhất và
không làm giảm tỷ lệ nhận diện bệnh xoăn vàng lá (Yellow Leaf Curl). Đây là
ngưỡng tạm thời cho đến khi có bộ mask đốm bệnh tô tay (ground truth).

### Giới hạn đã biết (Known Limitations)

- Hàm `_fill_largest_contour` tự động lấp đầy (tô trắng) các lỗ thủng vật lý
  nằm bên trong contour, ví dụ vết sâu ăn thủng hoặc đốm hoại tử rụng rời thành
  lỗ.
- GrabCut dựa vào màu lá và nền xung quanh nên nền đồng nhất hoặc bóng có
  màu gần mô lá vẫn có thể bị nhận nhầm. Khe hẹp hơn kernel closing 5×5 có
  thể bị nối. Các contour nhỏ hơn 3% diện tích contour lớn nhất bị loại;
  vùng lá tách xa seed xanh có thể bị bỏ sót khỏi `leaf_mask`.

### Xem trực quan segmentation

Có thể kiểm tra trực tiếp một ảnh hoặc cả thư mục ảnh mà không chạy classifier,
không cần `test_train_classifier` hay `train_classifier`. Chạy từ thư mục
`backend/`:

```powershell
python -m experiments.visualize_segmentation dataset\splits\test.txt --out experiments\output\segmentation-review --show
```

Mỗi ảnh kết quả gồm ảnh gốc, ảnh sau tiền xử lý, `leaf_mask`, `lesion_mask`
và overlay màu (lá xanh, đốm đỏ). Panel PNG được lưu vào `--out`; bỏ `--show`
nếu chỉ muốn lưu kết quả. Có thể truyền đường dẫn một ảnh hoặc thư mục ảnh
thay cho file split; đường dẫn trong file split được tính tương đối từ
`dataset/`.

## 5. Kết quả trả về

`pipeline.run(image)` trả `PipelineResult`, các trường khớp một-một với cột của `diagnosis_histories` (xem [database.md](database.md)):

| Trường | Tính ở đâu | Cột database |
|---|---|---|
| `disease_code`, `disease_confidence` | `classifier.predict` | `disease_id` (tra theo `diseases.code`), `disease_confidence` |
| `leaf_area_px` | Số điểm 255 trong `leaf_mask` | `leaf_area_px` |
| `lesion_area_px` | Số điểm 255 trong `lesion_mask` | `lesion_area_px` |
| `infected_ratio` | `lesion_area_px / leaf_area_px`, làm tròn 4 chữ số | `infected_ratio` |
| `severity_level` | `severity.severity_level()` trên số điểm ảnh (không dùng tỷ lệ đã làm tròn) | `severity_level` |
| `lesions`, `lesion_count` | `measure_lesions`, `len(lesions)` | `lesions`, `lesion_count` |
| `processed_image` | `draw_lesions` | `processed_image` |
| `steps` | Ảnh trung gian, theo `steps.ORDER` | Bảng `diagnosis_steps` |
| `recommendation` | `severity.IPM_RECOMMENDATIONS` | Không lưu, API trả kèm |

Diện tích lá và vết bệnh là **số điểm ảnh của mask**, không phải tổng diện tích contour.

## 6. Chạy thử và kiểm thử

Từ thư mục `backend/` (đã kích hoạt venv):

```powershell
# Chạy pipeline trên một ảnh, lưu ảnh từng bước vào ket_qua/
python -m image_processing.pipeline dataset\anh_thu\la_01.jpg --out ket_qua

# Test của pipeline và database
python manage.py test api image_processing experiments

# Đánh giá tách lá, vết bệnh và cấp độ so với 30 ảnh mask chuẩn (cần ảnh và mask trong dataset/)
python experiments/evaluate.py
```

Ảnh có tên tiếng Việt vẫn đọc được: dùng `pipeline.load_image()` thay cho `cv2.imread()` (hàm này trả `None` với đường dẫn có dấu trên Windows).

Test trong `image_processing/tests/` thay các giai đoạn bằng hàm giả để kiểm tra phần ghép nối. Khi viết xong module của mình, thêm test cho chính module đó (ví dụ ảnh tổng hợp một hình tròn xanh trên nền trắng → `leaf_mask` phải gần bằng diện tích hình tròn).

## 7. Model phân loại

- Huấn luyện bằng scikit-learn, nhãn là mã lớp PlantVillage, trùng `diseases.code` (ví dụ `Tomato___Early_blight`, `Tomato___healthy`).
- Model phải có `predict_proba`: `SVC(probability=True)` hoặc `RandomForestClassifier`. Nên bọc `StandardScaler` + model trong một `Pipeline` để lưu chung.
- Lưu bằng `joblib.dump(model, MODEL_PATH)` → `backend/image_processing/models/classifier.joblib`.
- Nhóm chưa chốt có commit file model vào git hay chia sẻ ngoài git (như ảnh trong `dataset/`).
