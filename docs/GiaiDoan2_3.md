# Chương: Giai đoạn 2–3 — Tách lá, tách vết bệnh và tính mức độ

## Mục tiêu

Giai đoạn 2 tạo mask của phiến lá, không gồm nền. Giai đoạn 3 tìm vùng mô đổi
màu rõ bên trong mask lá, đo diện tích và cung cấp số liệu cho công thức
mức độ nghiêm trọng. Hai mask cùng kích thước ảnh đã tiền xử lý 512×512, kiểu
`uint8`, chỉ có giá trị 0 và 255. Mask vết bệnh luôn là tập con của mask lá.

## Giai đoạn 2 — Tách lá

`segment_leaf(image)` nhận ảnh BGR `uint8` sau resize, khử nhiễu và CLAHE.
Ảnh được đổi sang HSV; pixel xanh bão hòa (H 25–95, S 40–255, V 30–255) làm
foreground seed. GrabCut khôi phục phần mô tối, nếp gập và cuống gần seed,
đồng thời dùng màu nền cục bộ để hạn chế bóng ngoài lá. Mask được closing
elip 5×5 một lần, sau đó tô contour lớn nhất và các contour có diện tích từ
3% contour lớn nhất trở lên.

`segment_leaf` được giữ nguyên trong phần tinh chỉnh này để không làm thay đổi
đầu vào/đầu ra của các giai đoạn sau. Hợp đồng đầy đủ nằm tại
[docs/pipeline.md](./pipeline.md).

## Giai đoạn 3 — Tách và đo vết bệnh

1. Tạo `healthy_mask` từ mô trong `leaf_mask` thuộc H 35–85, S ≥ 25, V ≥ 50.
2. Tạo vùng lõi bằng erosion elip với bán kính 3 px. Giới hạn này giảm từ 5 px
   để giảm mất mô bệnh sát mép nhưng vẫn hạn chế bóng biên.
3. Ứng viên vết bệnh là pixel không thuộc mô khỏe, có S ≥ 35 và V ≥ 50.
4. Dùng opening elip 3×3 để loại nhiễu nhỏ, closing elip 7×7 để nối vùng bệnh
   đứt đoạn; loại thành phần liên thông nhỏ hơn 12 pixel.
5. Giao kết quả với vùng lõi. Do hợp đồng yêu cầu vết bệnh nằm trong lá, pixel
   bị `segment_leaf` loại khỏi `leaf_mask` không thể được khôi phục ở giai đoạn
   3.

Các ngưỡng và kernel là hằng số trong
[segmentation.py](../backend/image_processing/segmentation.py). Không có
tham số runtime mới.

`measure_lesions()` lấy thành phần liên thông làm từng đốm, trả diện tích pixel,
chu vi contour, circularity, tâm và bounding box. `draw_lesions()` vẽ contour
đỏ lên ảnh BGR.

## Tính S và cấp độ

Gọi `A_leaf` là số pixel 255 của `leaf_mask`, `A_lesion` là số pixel 255 của
`lesion_mask`:

```text
S (%) = 100 × A_lesion / A_leaf
```

`severity.severity_level(A_lesion, A_leaf)` nhận số pixel chưa làm tròn, dùng
cùng ngưỡng cấp với pipeline. Nếu không có pixel lá, pipeline báo lỗi ảnh;
nếu mask chuẩn vết bệnh rỗng, `evaluate.py` không tính IoU/Dice cho ảnh đó và
ghi nhận báo nhầm khi `A_lesion > 0`.

## Đánh giá tham số

Đã chạy `python experiments/evaluate.py` trên 30 ảnh mask chuẩn và rà thêm 3
ảnh train có sẵn cho mỗi lớp (30 ảnh train tổng cộng, không trùng tập chuẩn).
Ảnh train không có mask vết bệnh chuẩn nên chỉ dùng để rà sanity-check, không
được dùng tính IoU/Dice. Trong 3 ảnh train lấy mẫu mỗi lớp, mask vết bệnh vẫn
không rỗng ở cả 3 ảnh khỏe và cả 3 ảnh xoăn vàng lá; hiện tượng này cũng có ở
baseline, nên bước rà train không chứng minh đã hết báo nhầm ở hai lớp đó.

| Chỉ số `evaluate.py` | Trước | Sau |
|---|---:|---:|
| Số ảnh chuẩn | 30 | 30 |
| IoU lá | 0.892 | 0.892 |
| IoU vết bệnh | 0.191 | 0.206 |
| Dice vết bệnh | 0.286 | 0.304 |
| Sai số S tuyệt đối trung bình (điểm %) | 7.49 | 7.13 |
| Đúng cấp | 53.3% | 53.3% |
| Lệch tối đa 1 cấp | 83.3% | 90.0% |
| Báo nhầm trên ảnh có mask bệnh rỗng | 8/9 | 7/9 |

| Lớp | IoU vết bệnh trước → sau | Sai số S trước → sau (điểm %) | Báo nhầm trước → sau |
|---|---:|---:|---:|
| Early blight | 0.198 → 0.145 | 25.88 → 25.28 | — |
| Target Spot | 0.127 → 0.232 | 1.64 → 0.58 | — |
| Lá khỏe | — | — | 3/3 → 3/3 |
| Xoăn vàng lá | — | — | 3/3 → 3/3 |
| Virus khảm | — | — | 2/3 → 1/3 |

Kết quả tổng thể được cải thiện, và Target Spot có IoU cao hơn sau khi tăng
ngưỡng Value và chỉnh kernel. Tuy vậy, báo nhầm trên lá khỏe và xoăn vàng lá
vẫn còn 6/6. Early blight cũng còn IoU thấp; một ảnh trong tập chuẩn có
24.376/31.944 pixel mask bệnh nằm ngoài `leaf_mask` dự đoán. Giai đoạn 3 không
thể khôi phục các pixel này mà không vi phạm hợp đồng mask con hoặc thay đổi
`segment_leaf`. Vì thế các số liệu này cần được xem là tiến triển một phần,
không phải đã đạt mọi tiêu chí chấp nhận.

## Hình minh họa

Từ thư mục `backend/`, chạy trên bộ mask chuẩn:

```powershell
python experiments/visualize_morphology.py --out experiments\output\morphology
```

Script dùng backend Matplotlib `Agg`; lưu panel ảnh gốc, mask lá, mask bệnh
trước/sau Opening và Closing, mask cuối và contour vào `experiments/output/`.
Các phép Opening/Closing minh họa trên mask lá chỉ để so sánh hình thái, không
được gọi trong `segment_leaf`. Hình `examples_correct_vs_wrong.png` chọn ví dụ
IoU cao/thấp, báo nhầm và đúng âm theo mask chuẩn.
