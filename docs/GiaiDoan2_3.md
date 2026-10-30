# Chương: Giai đoạn 2–3 — Tách lá, tách vết bệnh và tính mức độ

## Mục tiêu

Giai đoạn 2 tạo mask của phiến lá, không gồm nền. Giai đoạn 3 tìm vùng mô đổi
màu rõ bên trong mask lá, đo diện tích và cung cấp số liệu cho công thức
mức độ nghiêm trọng. Hai mask cùng kích thước ảnh đã tiền xử lý 512×512, kiểu
`uint8`, chỉ có giá trị 0 và 255. Mask vết bệnh luôn là tập con của mask lá.

## Giai đoạn 2 — Tách lá

`segment_leaf(image)` nhận ảnh BGR `uint8` sau resize, khử nhiễu và CLAHE.
Ảnh được đổi sang HSV; pixel xanh bão hòa (H 25–95, S 40–255, V 30–255) làm
seed foreground. Khoảng cách tới seed xác định vùng GrabCut được phép xem là
foreground/background có khả năng; pixel ở viền ảnh, vùng trung tính và Hue
màu ấm được hạn chế để giảm nhận nhầm nền. GrabCut chạy 5 vòng, khôi phục
mô tối và cuống gần seed. Sau GrabCut, pixel mô màu ấm gần seed (Hue 15–24
hoặc 165–179, S ≥ 50, V ≥ 40, cách seed không quá 20 px) được khôi phục để
giữ mép hoại tử.

Mask sau đó được closing bằng kernel ellipse 5×5 một lần. Cuối cùng, tô contour
lớn nhất và các contour có diện tích ít nhất 3% contour lớn nhất. Kết quả là
`leaf_mask` nhị phân, có cả vùng bệnh bên trong phiến lá.

`segment_leaf` được giữ nguyên trong phần tinh chỉnh này để không làm thay đổi
đầu vào/đầu ra của các giai đoạn sau. Hợp đồng đầy đủ nằm tại
[docs/pipeline.md](./pipeline.md).

## Giai đoạn 3 — Tách và đo vết bệnh

`segment_lesions(image, leaf_mask)` so màu từng pixel với mô xanh khỏe của
chính chiếc lá, thay vì dùng một ngưỡng Hue/Saturation chung cho mọi ảnh:

1. Tạo vùng tham chiếu mô khỏe trong `leaf_mask` với Hue 40–85, S ≥ 40 và
   V ≥ 40. Nếu có ít nhất 100 pixel tham chiếu, lấy trung vị LAB của vùng này;
   nếu không đủ, dùng mốc LAB dự phòng `(124, -14, 16)` (a*, b* theo thang đã
   trừ 128 của OpenCV).
2. Tạo ứng viên đổi màu nếu a* tăng ít nhất 12 so với mốc xanh; hoặc a* tăng
   ít nhất 3 đồng thời b* tăng ít nhất 8 (vàng đậm); hoặc pixel không thuộc
   Hue xanh 35–85, a* không giảm và L* tối hơn mốc ít nhất 20 (mô hoại tử tối).
   Ứng viên cần V ≥ 30 và chroma ít nhất 8; mô chết tối nằm sâu trong lá
   được bỏ điều kiện chroma nhưng vẫn cần V ≥ 30.
3. Loại bóng đổ ít màu và tối (chroma < 10, V < 90) trong dải 15 px sát mép.
   Ngoại lệ mô chết tối chỉ được giữ ở lõi lá: cách biên hơn 25 px, tối hơn
   mốc ít nhất 20 đơn vị L* và a* tăng ít nhất 5.
4. Erode `leaf_mask` bằng kernel ellipse 11×11 để tạo `leaf_core`, tức loại
   vùng cách biên lá tối đa 5 px. Chỉ giữ các ứng viên bên trong vùng lõi.
5. Opening ellipse 5×5 loại nhiễu nhỏ; Closing ellipse 5×5 nối vùng đốm gần
   nhau. Giao mask sau Closing với `leaf_core`, rồi bỏ thành phần liên thông
   nhỏ hơn 40 pixel. Kết quả cuối luôn là tập con của `leaf_mask`.

Các ngưỡng, luật bóng đổ và kernel là hằng số trong
[segmentation.py](../backend/image_processing/segmentation.py); không có tham
số runtime mới.

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

## Đánh giá trên 30 mask chuẩn

Số liệu dưới đây lấy từ `python experiments/evaluate.py` chạy trên commit
`62cbe6b`, với 30 ảnh mask chuẩn của việc 1D. Cột “Trước 2C” giữ số liệu baseline đã ghi nhận
trước khi chốt thuật toán LAB; cột main phản ánh mã segmentation hiện tại.

| Chỉ số `evaluate.py` | Trước 2C | Main `62cbe6b` |
|---|---:|---:|
| Số ảnh chuẩn | 30 | 30 |
| IoU lá | 0.892 | 0.892 |
| IoU vết bệnh | 0.191 | 0.216 |
| Dice vết bệnh | 0.286 | 0.320 |
| Sai số S tuyệt đối trung bình (điểm %) | 7.49 | 6.54 |
| Đúng cấp | 53.3% | 50.0% |
| Lệch ≤ 1 cấp | 83.3% | 90.0% |
| Báo nhầm trên ảnh có mask bệnh rỗng | 8/9 | 6/9 |

| Lớp | IoU vết bệnh trước 2C → main | Sai số S trước 2C → main (điểm %) | Báo nhầm trước 2C → main |
|---|---:|---:|---:|
| Early blight | 0.198 → 0.146 | 25.88 → 28.55 | — |
| Target Spot | 0.127 → 0.198 | 1.64 → 0.80 | — |
| Xoăn vàng lá (virus) | — | — | 3/3 → 3/3 |
| Khảm (virus) | — | — | 2/3 → 1/3 |
| Lá khỏe | — | — | 3/3 → 2/3 |

IoU/Dice vết bệnh và sai số S trung bình toàn bộ được cải thiện; tỷ lệ đúng
cấp giảm từ 53.3% xuống 50.0%, nhưng tỷ lệ lệch không quá 1 cấp tăng từ 83.3%
lên 90.0%, tức các ảnh sai cấp nằm gần cấp đúng hơn. Kết quả theo lớp không đồng nhất: Early blight
có IoU giảm và sai số S tăng, trong khi Target Spot cải thiện cả IoU và sai số
S. Một ảnh Early blight (`RS_Erly.B 7617`) có 24.376/31.944 pixel mask bệnh
nằm ngoài `leaf_mask` dự đoán. Giai đoạn 3 không thể khôi phục các pixel này
mà không vi phạm hợp đồng mask con hoặc thay đổi `segment_leaf`.

Ca Septoria `Matt.S_CG 1072` sai theo kiểu khác. Phần lá còn sống có màu xanh
vàng nên không có pixel nào đạt điều kiện mô khỏe tham chiếu (0 pixel trong
`healthy_mask`), hàm phải dùng mốc dự phòng `HEALTHY_REF_FALLBACK_LAB`. So với
mốc xanh của lá khỏe, mô xanh vàng bị tính là vết bệnh: 44.815 pixel báo nhầm,
khoảng 69% phần mô không bệnh theo mask chuẩn. Trong khi đó, mảng mô chết nâu
lại nằm ngoài `leaf_mask` dự đoán (60.785/71.480 pixel mask bệnh chuẩn). S dự
đoán là 67.5% so với S thật 52.4%; cấp vẫn đúng (Cấp 4) chỉ vì cả hai đều trên
35%. Hình `13_..._Matt.S_CG 1072_morphology.png` cho thấy rõ hai lỗi này.

## Hình minh họa

Từ thư mục `backend/`, chạy trên bộ mask chuẩn:

```powershell
python experiments/visualize_morphology.py --out experiments\output\morphology
```

Script dùng backend Matplotlib `Agg`; lưu panel ảnh sau tiền xử lý, mask lá, mask bệnh
qua seed xanh, GrabCut, Closing, tô contour, mask bệnh trước/sau Opening và
Closing, mask cuối sau giao `leaf_core`/lọc thành phần và contour vào
`experiments/output/`. Hình `examples_correct_vs_wrong.png` chọn bốn trường
hợp: IoU cao, IoU thấp, báo nhầm và đúng âm. Màu so sánh thống nhất với
`evaluate.py`: xanh lá là đúng, đỏ là báo nhầm, xanh dương là bỏ sót.
