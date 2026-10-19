# TÀI LIỆU TỔNG QUAN DỰ ÁN (PROJECT CHARTER & TECHNICAL SPEC)

- **Học phần:** Xử lý ảnh số (Digital Image Processing)
- **Trọng số điểm:** 20%
- **Quy mô nhóm:** 04 Thành viên
- **Tên đề tài (VI):** Hệ Thống Phát Hiện, Phân Loại Và Đo Lường Mức Độ Nghiêm Trọng Của Bệnh Trên Lá Cà Chua Dựa Trên Xử Lý Ảnh Số
- **Tên đề tài (EN):** Tomato Leaf Disease Detection, Classification, and Severity Estimation System using Digital Image Processing

---

## 1. Đặt vấn đề & Mục tiêu Dự án

### 1.1. Đặt vấn đề (Problem Statement)
Các hệ thống nhận diện bệnh cây trồng phổ biến hiện nay thường chỉ dừng lại ở bài toán phân loại (Classification) — tức là chỉ xác định tên bệnh. Tuy nhiên, trong quy trình Quản lý dịch hại tổng hợp (IPM) ngoài thực tế, kỹ sư nông học và chủ trang trại cần biết chính xác **tỷ lệ phần trăm diện tích lá bị nhiễm bệnh** để đối chiếu với Ngưỡng hành động (Action Threshold) và tính toán liều lượng thuốc bảo vệ thực vật. Việc ước lượng bằng mắt thường có sai số lớn từ 15% đến 25%.

### 1.2. Mục tiêu Dự án (Objectives)
1. **Về mặt Xử lý ảnh (Trọng tâm 80%):** Xây dựng Pipeline xử lý ảnh số từ khử nhiễu, cân bằng sáng cục bộ (CLAHE), biến đổi không gian màu (RGB, HSV, CIELAB), phân ngưỡng tự động (Otsu), xử lý hình thái học (Morphology) đến trích xuất đường biên (Contours) để đo lường tỷ lệ diện tích tổn thương trên phiến lá.
2. **Về mặt Phân loại (Trọng tâm 20%):** Trích xuất đặc trưng kết cấu (GLCM), đặc trưng màu sắc (Color Moments) kết hợp mô hình học máy (SVM / Random Forest) hoặc mạng CNN nhẹ (MobileNetV2) để định danh tên bệnh trên lá Cà chua (tập dữ liệu chuẩn PlantVillage).
3. **Về mặt Ứng dụng (Web Application):** Xây dựng hệ thống Web trực quan hóa toàn bộ kết quả ảnh qua từng bước biến đổi, trả về phần trăm diện tích bệnh, cấp độ cảnh báo (Cấp 0 - Cấp 4) và khuyến nghị xử lý IPM.

---

## 2. Quy trình Kỹ thuật Cốt lõi (5-Stage Pipeline)

### Giai đoạn 1: Thu nhận & Tiền xử lý ảnh (Image Preprocessing)
- **Chuẩn hóa kích thước:** Resize ảnh đầu vào về kích thước chuẩn `256x256` hoặc `512x512` pixels.
- **Khử nhiễu bảo toàn cạnh:** Áp dụng bộ lọc `Bilateral Filter` (d=9, sigmaColor=75, sigmaSpace=75) hoặc `Median Blur` (kernel 5x5) để loại bỏ nhiễu hạt mà không làm mờ ranh giới đốm bệnh.
- **Cân bằng độ tương phản cục bộ:** Chuyển ảnh từ `RGB` sang `CIELAB`. Áp dụng thuật toán `CLAHE` (clipLimit=2.0, tileGridSize=8x8) lên kênh độ sáng `L`, sau đó chuyển ngược về `RGB`.

### Giai đoạn 2: Phân vùng tách Phiến lá khỏi Nền (Leaf Segmentation)
- Chuyển ảnh sang không gian màu `HSV`.
- Phân ngưỡng trên kênh `S` (Saturation) kết hợp thuật toán `Otsu's Thresholding` hoặc `cv2.inRange` để tách toàn bộ phiến lá khỏi nền.
- Áp dụng phép toán hình thái học `Closing` (kernel elip 5x5) để lấp đầy các lỗ khuyết bên trong mặt nạ lá, thu được `Mask_leaf`.
- Đếm tổng số pixel khác 0 trên `Mask_leaf` để lấy **Tổng diện tích phiến lá (A_leaf)**.

### Giai đoạn 3: Phân vùng Đốm bệnh & Hình thái học (Lesion Segmentation)
- Dùng `cv2.bitwise_and` giữa ảnh đã tiền xử lý và `Mask_leaf` để trích xuất vùng quan tâm (ROI).
- Tạo mặt nạ vùng mô lá xanh khỏe mạnh (`Mask_healthy`, dải màu Hue từ 35 đến 85 trong HSV) hoặc phân cụm K-Means (K=3) trên kênh `a*` của không gian màu `CIELAB`.
- Tách mặt nạ vết bệnh: `Mask_lesion = Mask_leaf - Mask_healthy`.
- Áp dụng phép toán `Opening` (kernel 3x3) để xóa nhiễu điểm và `Closing` để nối liền ổ dịch.
- Dùng `cv2.findContours()` vẽ đường viền đỏ quanh vết bệnh trên ảnh gốc và tính **Tổng diện tích vùng bệnh (A_lesion)**.

### Giai đoạn 4: Trích xuất Đặc trưng & Phân loại Tên bệnh (Classification)
- **Đặc trưng kết cấu (Texture):** Tính ma trận đồng xuất hiện mức xám `GLCM` (Contrast, Dissimilarity, Homogeneity, Energy, Correlation).
- **Đặc trưng màu sắc (Color):** Tính Mean, Standard Deviation, Skewness trên 3 kênh H, S, V.
- **Mô hình phân loại:** Đưa vector đặc trưng vào `SVM` / `Random Forest` (hoặc đối sánh với `MobileNetV2`).

### Giai đoạn 5: Định lượng Mức độ Nghiêm trọng & Khuyến nghị (Severity Estimation)
- **Công thức tính tỷ lệ diện tích bệnh:** `S (%) = (A_lesion / A_leaf) * 100%`
- **Thang đo phân cấp và khuyến nghị IPM:**
  - **Cấp 0 (S = 0%):** Lá khỏe mạnh hoàn toàn -> Duy trì chăm sóc định kỳ.
  - **Cấp 1 (0% < S < 5%):** Nhiễm nhẹ -> Cắt tỉa lá bệnh, phun phòng chế phẩm sinh học (Trichoderma).
  - **Cấp 2 (5% <= S < 15%):** Trung bình (Ngưỡng hành động IPM) -> Phun thuốc đặc trị liều tiêu chuẩn.
  - **Cấp 3 (15% <= S <= 35%):** Nặng -> Phun thuốc đặc trị liều tăng cường, cách ly khu vực bệnh, ngưng bón phân đạm.
  - **Cấp 4 (S > 35%):** Nguy kịch -> Nhổ bỏ và tiêu hủy cây nhiễm nặng, xử lý đất bằng vôi bột.

---

## 3. Kiến trúc Công nghệ (Tech Stack)
- **Xử lý ảnh & Học máy:** Python 3.10+, OpenCV (`cv2`), NumPy, Scikit-image, Scikit-learn, Matplotlib.
- **Backend API:** Django REST Framework (hoặc FastAPI).
- **Frontend UI:** React.js (Vite) + Material UI (MUI).
- **Quản lý & Triển khai:** Git/GitHub, Docker & Docker Compose.

---

## 4. Phân công Nhiệm vụ (Work Breakdown Structure - 4 Thành viên)

| Thành viên | Vai trò phụ trách | Công việc cụ thể | Đầu ra bàn giao (Deliverables) |
| :--- | :--- | :--- | :--- |
| **Thành viên 1** | Data & Preprocessing Lead | Chuẩn hóa dataset PlantVillage (Lá cà chua); cài đặt lọc nhiễu Bilateral/Median, biến đổi màu RGB-LAB-HSV và cân bằng sáng CLAHE; xuất biểu đồ Histogram. | Module `preprocessing.py` + Bộ ảnh chuẩn + Phân tích Histogram. |
| **Thành viên 2** | Segmentation & Morphology Lead | Cài đặt thuật toán tách nền lá (`Mask_leaf`), tách đốm bệnh (`Mask_lesion`), toán tử Opening/Closing, vẽ Contours và tính tỷ lệ `S (%)`. | Module `segmentation.py` + Hàm xuất ảnh trung gian & chỉ số diện tích. |
| **Thành viên 3** | Feature Extraction & AI Lead | Trích xuất đặc trưng GLCM, Color Moments; huấn luyện mô hình phân loại (SVM/Random Forest hoặc MobileNetV2); xuất Confusion Matrix, F1-Score. | Module `classifier.py` + File trọng số model + Bảng số liệu đánh giá. |
| **Thành viên 4** | Full-Stack Web & Integration Lead | Xây dựng REST API ghép nối 3 module xử lý ảnh; thiết kế giao diện React.js hiển thị trực quan chuỗi ảnh từng bước, thanh đo cấp độ bệnh và khuyến nghị. | Source code Backend + Frontend + Docker Compose. |

---

## 5. Kế hoạch Thực hiện (Timeline 4 Tuần)
- **Tuần 1:** Chốt 4-5 lớp bệnh lá cà chua từ PlantVillage; khởi tạo Git repo; thống nhất Input/Output giữa các module.
- **Tuần 2:** Phát triển độc lập 3 module xử lý ảnh (`preprocessing.py`, `segmentation.py`, `classifier.py`) và dựng giao diện Web cơ bản.
- **Tuần 3:** Tích hợp toàn bộ Pipeline vào Backend API; kiểm thử và tinh chỉnh ngưỡng màu HSV, kích thước kernel Morphology.
- **Tuần 4:** Xuất bảng số liệu thực nghiệm, hoàn thiện báo cáo cuối kỳ, slide thuyết trình và chạy thử Demo.