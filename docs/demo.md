# Kịch bản demo

Kịch bản chạy trên **bản Docker** (`docker compose up`), khoảng 12–15 phút. Cập nhật theo giao diện mới (PR #36, #37). Mỗi bước ghi thao tác, điều cần chỉ cho người xem và kết quả phải thấy. Kết quả khác đi ở bước nào thì dừng lại ghi vào mục [Lỗi gặp khi chạy thử](#lỗi-gặp-khi-chạy-thử).

## 1. Bộ ảnh mẫu

Ảnh lấy từ **tập test** (mô hình chưa thấy lúc huấn luyện), chọn bằng script:

```powershell
# từ thư mục backend/, cần ảnh PlantVillage trong dataset/plantvillage/
python experiments/pick_demo_images.py
```

Script chạy pipeline giống hệt trên web với 20 ảnh mỗi lớp rồi chọn:
- **mỗi lớp một ảnh**: mô hình đoán đúng, trang kết quả không hiện cảnh báo nào, độ tin cậy cao nhất;
- **một ảnh có cảnh báo độ tin cậy thấp** (dưới 0,55), ưu tiên ảnh mô hình đoán sai để demo nút "Báo kết quả sai";
- **một ảnh không dùng được**: ảnh mặt bàn không có lá do script tự tạo.

Ảnh được chép vào `backend/experiments/output/demo/` (không đưa lên git, nhóm chia sẻ riêng) kèm `demo_images.csv`.

Kết quả chọn ngày 30/10/2026 trên bộ ảnh đủ (3.632 ảnh test), mô hình SVM của 3E, ngưỡng cảnh báo 0,55. Script đọc ảnh đúng như web (xóa EXIF rồi lưu lại JPG), nên số trong bảng khớp màn hình lúc demo. Mỗi lớp lấy mẫu bằng bộ sinh ngẫu nhiên riêng, nên lớp này thiếu hay thêm ảnh không làm đổi ảnh của lớp khác. Chạy lại script thì bảng có thể khác nếu mô hình, bước tách vết bệnh hoặc bộ ảnh thay đổi.

| File | Vai trò | Lớp thật | Kết quả trên web | Độ tin cậy | Cấp | Cảnh báo |
|---|---|---|---|---:|---:|---|
| `01_Bacterial_spot.jpg` | mỗi lớp một ảnh | Đốm vi khuẩn | Đốm vi khuẩn | 1,00 | 1 | không |
| `02_Early_blight.jpg` | mỗi lớp một ảnh | Đốm vòng | Đốm vòng | 1,00 | 1 | không |
| `03_Late_blight.jpg` | mỗi lớp một ảnh | Mốc sương | Mốc sương | 1,00 | 1 | không |
| `04_Leaf_Mold.jpg` | mỗi lớp một ảnh | Mốc lá | Mốc lá | 1,00 | 1 | không |
| `05_Septoria_leaf_spot.jpg` | mỗi lớp một ảnh | Đốm lá Septoria | Đốm lá Septoria | 1,00 | 1 | không |
| `06_Spider_mites Two-spotted_spider_mite.jpg` | mỗi lớp một ảnh | Nhện đỏ hai chấm | Nhện đỏ hai chấm | 1,00 | 1 | không |
| `07_Target_Spot.jpg` | mỗi lớp một ảnh | Đốm đích | Đốm đích | 1,00 | 1 | không |
| `08_Tomato_Yellow_Leaf_Curl_Virus.jpg` | mỗi lớp một ảnh | Xoăn vàng lá | Xoăn vàng lá | 1,00 | 1 | không |
| `09_Tomato_mosaic_virus.jpg` | mỗi lớp một ảnh | Khảm lá | Khảm lá | 0,99 | 0 | không |
| `10_healthy.jpg` | mỗi lớp một ảnh | Lá khỏe | Lá khỏe | 1,00 | 0 | không |
| `11_do_tin_cay_thap.jpg` | cảnh báo độ tin cậy thấp | Đốm lá Septoria | **Mốc sương (sai)** | 0,52 | 3 | độ tin cậy thấp |
| `12_khong_dung_duoc.png` | ảnh không dùng được | (không có lá) | Lỗi: "Không tìm thấy lá trong ảnh. Hãy chụp một chiếc lá trên nền đơn sắc." | | | |

Ảnh độ tin cậy thấp được chọn theo thứ tự ưu tiên: chỉ có đúng cảnh báo này (dễ giải thích), mô hình đoán sai (để demo nút "Báo kết quả sai"), độ tin cậy gần ngưỡng nhất.

## 2. Chuẩn bị (trước buổi demo)

1. Mở Docker Desktop. Từ thư mục gốc repo: `docker compose up --build -d`, đợi `docker compose ps` báo đủ 3 dịch vụ chạy (`db` là *healthy*).
2. Tạo tài khoản quản trị nếu chưa có: `docker compose exec backend python manage.py createsuperuser`.
3. Chép thư mục ảnh mẫu ra màn hình cho dễ chọn.
4. Mở **cửa sổ ẩn danh** của trình duyệt tại http://localhost:8080 (không còn phiên đăng nhập cũ). Mở thêm một tab `/admin/` đã đăng nhập bằng tài khoản quản trị.

## 3. Các bước

| # | Thao tác | Chỉ cho người xem | Phải thấy |
|---|---|---|---|
| 1 | **Đăng ký**: mở `/register`, nhập email, họ tên, mật khẩu; bấm link điều khoản rồi tick đồng ý | Mật khẩu yếu bị từ chối (thử `12345678`); phải đồng ý điều khoản mới đăng ký được | Đăng ký xong vào thẳng trang **Tải ảnh**; menu Tải ảnh, Lịch sử, Báo lỗi, Tài khoản (trên điện thoại menu nằm ở đáy màn hình) |
| 2 | **Tải ảnh**: bấm vào khung (hoặc kéo thả) chọn `02_Early_blight.jpg`, bấm **Chẩn đoán** | Khung "Mẹo chụp ảnh" (nên / không nên); chỉ nhận JPG/PNG tối đa 10 MB; pipeline chạy ngay, khoảng 1–3 giây | Dưới ảnh xem trước có tên file, dung lượng, kích thước (256×256 px); bấm Chẩn đoán thì chuyển sang trang **Kết quả** |
| 3 | **Tóm tắt kết quả**: xem card "Kết quả chẩn đoán" | Tên bệnh, thanh độ tin cậy, tỷ lệ S = diện tích vết bệnh / diện tích lá, số đốm, thanh 5 cấp kèm khoảng S | Bệnh đốm vòng (úa sớm), độ tin cậy 99.6%, S = 3.51%, 17 đốm, Cấp 1 - Nhiễm nhẹ; không có khung cảnh báo màu cam |
| 4 | **So sánh trước / sau**: kéo thanh chia trên ảnh ở card "Ảnh phân tích" | Bên trái là ảnh lá đã chuẩn hóa 512×512, bên phải là ảnh đã khoanh viền đỏ quanh vết bệnh; link "Mở ảnh gốc đã tải lên" | Kéo tới đâu ảnh đổi tới đó |
| 5 | **Lớp phủ và bảng đốm**: bấm **Lớp phủ mặt nạ**, rồi rê chuột (hoặc chạm) vào một dòng trong bảng "Chi tiết từng đốm bệnh" | Mặt nạ vết bệnh tô đỏ, khung vàng quanh từng đốm; bật/tắt mặt nạ lá, chỉnh độ đậm; bảng diện tích, % diện tích lá, chu vi, độ tròn, tâm của từng đốm | Đốm của dòng đang chọn được khoanh đậm kèm số `#`; bảng hiện 8 đốm lớn nhất, "Xem thêm 9 đốm" ra đủ 17 |
| 6 | **Khuyến nghị**: xem card khuyến nghị theo cấp và card "Khuyến nghị cho …" | Khuyến nghị theo cấp (IPM) và theo bệnh (tác nhân, cách xử lý, nguồn tham khảo) | Có cả hai khuyến nghị, link nguồn mở được |
| 7 | **Các bước xử lý**: cuộn xuống "Các bước xử lý ảnh", bấm một ảnh | 9 ảnh trung gian chia 3 giai đoạn: tiền xử lý (chuẩn hóa kích thước, khử nhiễu, CLAHE), tách lá (kênh S, mặt nạ lá), tách vết bệnh (vùng lá, mô lá khỏe, mặt nạ vết bệnh trước và sau hình thái học) | Đủ 9 ảnh, đúng thứ tự; bấm vào thì ảnh phóng to |
| 8 | **Histogram CLAHE**: xem card cuối trang | Phân bố độ sáng L* trước và sau CLAHE, tính ngay trên trình duyệt từ ảnh hai bước | Trung bình L* 47,7 → 53,3, độ lệch chuẩn 17,5 → 18,8 |
| 9 | **Lưu**: kéo lên đầu trang, bấm **Lưu kết quả** | Đánh dấu kết quả để xem lại | Nút đổi thành **Đã lưu** |
| 10 | **In / Lưu PDF** (tùy chọn): bấm nút, xem bản xem trước rồi Hủy | Bản in ẩn menu và các nút, giữ đủ ảnh, bảng đốm (đủ 17 dòng), các bước và histogram | Đầu trang in có dòng "Kết quả #…" |
| 11 | **Bệnh virus**: tải ảnh Xoăn vàng lá (`08_Tomato_Yellow_Leaf_Curl_Virus.jpg`) | Bệnh virus không có thuốc chữa: chỉ hiện khuyến nghị theo bệnh (nhổ bỏ cây, kiểm soát bọ phấn) | Bệnh xoăn vàng lá; không có card "Khuyến nghị IPM theo cấp độ" |
| 12 | **Độ tin cậy thấp**: tải ảnh `11_do_tin_cay_thap.jpg` (lá Đốm lá Septoria) | Mô hình đoán nhầm thành Mốc sương nhưng chưa chắc chắn, nên trang cảnh báo người dùng; thanh độ tin cậy chuyển màu cam | Bệnh mốc sương, khung cam "Độ tin cậy chỉ 52.4%, thấp hơn ngưỡng 55%" |
| 13 | **Phản hồi**: bấm **Báo kết quả sai** trong khung cảnh báo, nhập mô tả (ví dụ "Lá này là đốm lá Septoria"), gửi | Tiêu đề được điền sẵn; phản hồi gắn với lần chẩn đoán này | Thông báo "Đã gửi phản hồi" |
| 14 | **Ảnh không dùng được**: tải `12_khong_dung_duoc.png` (ảnh mặt bàn không có lá) | Ảnh không có lá thì hệ thống báo rõ thay vì đoán bừa | Trang "Không chẩn đoán được ảnh này", thông báo "Không tìm thấy lá trong ảnh. Hãy chụp một chiếc lá trên nền đơn sắc." và nút "Chọn ảnh khác" |
| 15 | **Lịch sử**: mở **Lịch sử**, chuyển giữa **Tất cả** và **Đã lưu** | Mỗi người chỉ thấy lịch sử của mình, mới nhất trước, có ảnh thu nhỏ và cấp độ | Tất cả có 4 mục (kể cả mục "Lỗi"); Đã lưu có 1 mục (bước 9); bấm vào mở lại đúng kết quả |
| 16 | **Quản trị**: sang tab `/admin/`, mở **Phản hồi** | Quản trị viên xem phản hồi kèm lần chẩn đoán, đổi trạng thái duyệt | Thấy phản hồi ở bước 13 |

Phần thêm nếu còn thời gian: trang **Báo lỗi** (gửi lỗi ứng dụng, xem trong `/admin/`), **Tài khoản → Xóa tài khoản** (nhập lại mật khẩu, bị đăng xuất, đăng nhập lại bị từ chối), mở trang kết quả trên điện thoại.

## 4. Kiểm tra trước buổi demo

Chạy trọn bảng trên với bản Docker build từ `main` mới nhất, đánh dấu từng bước:

- [ ] Bước 1–16 chạy đúng, không có lỗi trên màn hình
- [ ] Không có request lỗi (đỏ) trong tab Network của DevTools, trừ lỗi cố ý ở bước 1 (mật khẩu yếu)
- [ ] `docker compose logs backend` không có traceback
- [ ] Tắt (`docker compose down`) rồi bật lại: tài khoản và lịch sử vẫn còn

## Lỗi gặp khi chạy thử

| Ngày | Bước | Lỗi | Cách xử lý |
|---|---|---|---|
| 30/10/2026 | 12 (độ tin cậy thấp) | Ảnh chọn bằng script ra 0,52 nhưng trên web chỉ 0,29 và khác tên bệnh | Web xóa EXIF và lưu lại JPG nên điểm ảnh đổi nhẹ; ảnh sát ngưỡng đổi kết quả. Sửa script đọc ảnh đúng như web (`load_as_web`), chọn lại ảnh |
| 30/10/2026 | (chọn ảnh) | Bộ ảnh trên máy TV4 thiếu ảnh Xoăn vàng lá; vì 10 lớp dùng chung một bộ sinh ngẫu nhiên nên ảnh của Khảm lá, Lá khỏe cũng khác người dùng bộ ảnh đủ | Bổ sung đủ ảnh; mỗi lớp dùng bộ sinh ngẫu nhiên riêng; chọn lại ảnh và chạy lại kịch bản |
| 31/10/2026 | (cả kịch bản) | Giao diện mới (#36, #37): ảnh gốc thay bằng thanh so sánh trước/sau, thêm lớp phủ, bảng đốm, histogram CLAHE, nút In | Viết lại kịch bản thành 16 bước, chạy lại trọn trên bản build giao diện mới: kết quả không đổi |
