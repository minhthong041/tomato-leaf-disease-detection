# Kịch bản demo

Kịch bản chạy trên **bản Docker** (`docker compose up`), khoảng 10 phút. Mỗi bước ghi thao tác, điều cần chỉ cho người xem và kết quả phải thấy. Kết quả khác đi ở bước nào thì dừng lại ghi vào mục [Lỗi gặp khi chạy thử](#lỗi-gặp-khi-chạy-thử).

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

Kết quả chọn ngày 30/10/2026, mô hình SVM của 3E, ngưỡng cảnh báo 0,55. Script đọc ảnh đúng như web (xóa EXIF rồi lưu lại JPG), nên số trong bảng khớp màn hình lúc demo. Chạy lại script thì bảng có thể khác nếu mô hình hoặc bước tách vết bệnh thay đổi.

| File | Vai trò | Lớp thật | Kết quả trên web | Độ tin cậy | Cấp | Cảnh báo |
|---|---|---|---|---:|---:|---|
| `01_Bacterial_spot.jpg` | mỗi lớp một ảnh | Đốm vi khuẩn | Đốm vi khuẩn | 1,00 | 1 | không |
| `02_Early_blight.jpg` | mỗi lớp một ảnh | Đốm vòng | Đốm vòng | 0,95 | 3 | không |
| `03_Late_blight.jpg` | mỗi lớp một ảnh | Mốc sương | Mốc sương | 1,00 | 3 | không |
| `04_Leaf_Mold.jpg` | mỗi lớp một ảnh | Mốc lá | Mốc lá | 1,00 | 1 | không |
| `05_Septoria_leaf_spot.jpg` | mỗi lớp một ảnh | Đốm lá Septoria | Đốm lá Septoria | 1,00 | 2 | không |
| `06_Spider_mites Two-spotted_spider_mite.jpg` | mỗi lớp một ảnh | Nhện đỏ hai chấm | Nhện đỏ hai chấm | 0,99 | 1 | không |
| `07_Target_Spot.jpg` | mỗi lớp một ảnh | Đốm đích | Đốm đích | 1,00 | 1 | không |
| `08_Tomato_Yellow_Leaf_Curl_Virus.jpg` | mỗi lớp một ảnh | Xoăn vàng lá | Xoăn vàng lá | 1,00 | 3 | không |
| `09_Tomato_mosaic_virus.jpg` | mỗi lớp một ảnh | Khảm lá | Khảm lá | 1,00 | 0 | không |
| `10_healthy.jpg` | mỗi lớp một ảnh | Lá khỏe | Lá khỏe | 1,00 | 0 | không |
| `11_do_tin_cay_thap.jpg` | cảnh báo độ tin cậy thấp | Đốm đích | **Mốc lá (sai)** | 0,52 | 2 | độ tin cậy thấp |
| `12_khong_dung_duoc.png` | ảnh không dùng được | (không có lá) | Lỗi: "Không tìm thấy lá trong ảnh. Hãy chụp một chiếc lá trên nền đơn sắc." | | | |

Bộ ảnh nhóm dùng lần này thiếu một phần ảnh lớp Xoăn vàng lá (thiếu 418/1.071 ảnh test); script bỏ qua ảnh thiếu và báo ra màn hình.

## 2. Chuẩn bị (trước buổi demo)

1. Mở Docker Desktop. Từ thư mục gốc repo: `docker compose up --build -d`, đợi `docker compose ps` báo đủ 3 dịch vụ chạy (`db` là *healthy*).
2. Tạo tài khoản quản trị nếu chưa có: `docker compose exec backend python manage.py createsuperuser`.
3. Chép thư mục ảnh mẫu ra màn hình cho dễ chọn.
4. Mở **cửa sổ ẩn danh** của trình duyệt tại http://localhost:8080 (không còn phiên đăng nhập cũ). Mở thêm một tab `/admin/` đã đăng nhập bằng tài khoản quản trị.

## 3. Các bước

| # | Thao tác | Chỉ cho người xem | Phải thấy |
|---|---|---|---|
| 1 | **Đăng ký**: mở `/register`, nhập email, họ tên, mật khẩu; bấm link điều khoản rồi tick đồng ý | Mật khẩu yếu bị từ chối ngay (thử `12345678`); phải đồng ý điều khoản mới đăng ký được | Đăng ký xong vào thẳng trang **Tải ảnh**, menu có Lịch sử, Báo lỗi, Tài khoản |
| 2 | **Tải ảnh**: chọn ảnh lớp Đốm vòng (`02_Early_blight.jpg`), bấm **Chẩn đoán** | Chỉ nhận JPG/PNG tối đa 10 MB; pipeline chạy ngay, khoảng 1–3 giây | Chuyển sang trang **Kết quả** |
| 3 | **Ảnh và tên bệnh**: xem 2 ảnh trên cùng | Ảnh gốc và ảnh đã khoanh viền đỏ từng vết bệnh; tên bệnh kèm độ tin cậy | Bệnh đốm vòng (úa sớm), độ tin cậy khoảng 94,9%, không có khung cảnh báo màu cam |
| 4 | **Cấp độ**: xem thẻ kết quả | S = diện tích vết bệnh / diện tích lá; thanh 5 cấp tô đúng cấp | S khoảng 22%, Cấp 3 - Nặng |
| 5 | **Khuyến nghị**: xem khuyến nghị theo cấp và thẻ "Khuyến nghị cho …" | Khuyến nghị theo cấp (IPM) và theo bệnh (tác nhân, cách xử lý, nguồn tham khảo) | Có cả hai khuyến nghị, link nguồn mở được |
| 6 | **Các bước xử lý**: cuộn xuống "Các bước xử lý ảnh" | 9 ảnh trung gian: chuẩn hóa kích thước → khử nhiễu → CLAHE → kênh S → mặt nạ lá → vùng lá → mô lá khỏe → mặt nạ vết bệnh trước và sau hình thái học | Đủ 9 ảnh, đúng thứ tự |
| 7 | **Lưu**: bấm **Lưu kết quả** | Đánh dấu kết quả để xem lại | Nút đổi thành **Đã lưu** |
| 8 | **Bệnh virus**: tải ảnh Xoăn vàng lá (`08_Tomato_Yellow_Leaf_Curl_Virus.jpg`) | Bệnh virus không có thuốc chữa: chỉ hiện khuyến nghị theo bệnh (nhổ bỏ cây, kiểm soát bọ phấn) | Không có khuyến nghị "phun thuốc đặc trị" theo cấp |
| 9 | **Độ tin cậy thấp**: tải ảnh `11_do_tin_cay_thap.jpg` (lá Đốm đích) | Mô hình đoán nhầm thành Mốc lá nhưng chưa chắc chắn, nên trang cảnh báo người dùng | Bệnh mốc lá, khung cam "Độ tin cậy chỉ 52.4%, thấp hơn ngưỡng 55%" |
| 10 | **Phản hồi**: bấm **Báo kết quả sai** trong khung cảnh báo, nhập mô tả (ví dụ "Lá này là đốm đích"), gửi | Tiêu đề được điền sẵn; phản hồi gắn với lần chẩn đoán này | Thông báo "Đã gửi phản hồi" |
| 11 | **Ảnh không dùng được**: tải `12_khong_dung_duoc.png` (ảnh mặt bàn không có lá) | Ảnh không có lá thì hệ thống báo rõ thay vì đoán bừa | Thông báo "Không tìm thấy lá trong ảnh. Hãy chụp một chiếc lá trên nền đơn sắc." |
| 12 | **Lịch sử**: mở **Lịch sử**, chuyển giữa **Tất cả** và **Đã lưu** | Mỗi người chỉ thấy lịch sử của mình, mới nhất trước | Tất cả có 4 mục (kể cả mục lỗi); Đã lưu có 1 mục (bước 7); bấm vào mở lại đúng kết quả |
| 13 | **Quản trị**: sang tab `/admin/`, mở **Phản hồi** | Quản trị viên xem phản hồi kèm lần chẩn đoán, đổi trạng thái duyệt | Thấy phản hồi ở bước 10 |

Phần thêm nếu còn thời gian: trang **Báo lỗi** (gửi lỗi ứng dụng, xem trong `/admin/`), **Tài khoản → Xóa tài khoản** (nhập lại mật khẩu, bị đăng xuất, đăng nhập lại bị từ chối).

## 4. Kiểm tra trước buổi demo

Chạy trọn bảng trên với bản Docker build từ `main` mới nhất, đánh dấu từng bước:

- [ ] Bước 1–13 chạy đúng, không có lỗi trên màn hình
- [ ] Không có request lỗi (đỏ) trong tab Network của DevTools, trừ lỗi cố ý ở bước 1 (mật khẩu yếu)
- [ ] `docker compose logs backend` không có traceback
- [ ] Tắt (`docker compose down`) rồi bật lại: tài khoản và lịch sử vẫn còn

## Lỗi gặp khi chạy thử

| Ngày | Bước | Lỗi | Cách xử lý |
|---|---|---|---|
| 30/10/2026 | 9 | Ảnh chọn bằng script ra 0,52 nhưng trên web chỉ 0,29 và khác tên bệnh | Web xóa EXIF và lưu lại JPG nên điểm ảnh đổi nhẹ; ảnh sát ngưỡng đổi kết quả. Sửa script đọc ảnh đúng như web (`load_as_web`), chọn lại ảnh |
