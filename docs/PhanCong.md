# Phân công công việc và quy trình làm việc với Git

Tài liệu này giao việc cụ thể cho từng thành viên dựa trên khung code hiện có trên `main`, và quy định cách tạo nhánh, commit, mở PR. Phạm vi và vai trò: [TongQuanDuAn.md](TongQuanDuAn.md). Quy ước vào/ra giữa các module: [pipeline.md](pipeline.md).

| Thành viên | Vai trò | Họ tên | GitHub |
|---|---|---|---|
| Thành viên 1 | Tiền xử lý và dữ liệu | | |
| Thành viên 2 | Tách lá, tách đốm bệnh, hình thái học | | |
| Thành viên 3 | Trích xuất đặc trưng và phân loại | | |
| Thành viên 4 | Backend API, giao diện, tích hợp | | |

---

## 0. Việc cả nhóm chốt trước (một buổi họp)

- [ ] Duyệt danh sách **4–5 lớp bệnh**. Đề xuất: `Tomato___Early_blight`, `Tomato___Late_blight`, `Tomato___Septoria_leaf_spot`, `Tomato___Bacterial_spot` và `Tomato___healthy`. Tránh các lớp do virus và nhện đỏ: triệu chứng loang cả lá, không thành đốm, làm S% sai.
- [ ] Một người tải **PlantVillage** (bản gốc: https://github.com/spMohanty/PlantVillage-Dataset, thư mục `raw/color/`), chỉ giữ các lớp đã chọn, rồi chia sẻ cho cả nhóm qua Drive. Tất cả dùng **cùng một bản**.
- [ ] Chọn khoảng **30 ảnh** trong tập test để tô tay mask (Thành viên 2 phụ trách, mọi người có thể chia nhau tô).
- [ ] Ngưỡng **độ tin cậy** để hiển thị "chưa chắc chắn" (đề xuất 0.6), và cách xử lý khi phân loại nói "lá khỏe" nhưng S > 0.
- [ ] File model `.joblib`: commit vào git hay chia sẻ ngoài git.

### Cấu trúc thư mục dữ liệu (`backend/dataset/`, ảnh không đưa lên git)

```
backend/dataset/
├── plantvillage/           # ảnh PlantVillage, mỗi lớp một thư mục, tên thư mục = diseases.code
│   ├── Tomato___Early_blight/
│   └── ...
├── splits/                 # train.txt, test.txt — danh sách đường dẫn ảnh (ĐƯỢC commit)
├── masks/
│   ├── leaf/               # mask lá tô tay: cùng tên ảnh gốc, đuôi .png, trắng = lá
│   └── lesion/             # mask vết bệnh tô tay: trắng = vết bệnh
└── field/                  # ảnh tự chụp ngoài vườn, để thử độ bền
```

Riêng `splits/*.txt` được đưa lên git, để cả nhóm dùng chung một cách chia train/test.

---

## 1. Thành viên 1: tiền xử lý và dữ liệu

**Nhánh:** `tv1/tien-xu-ly` · **Người review:** Thành viên 2

| Việc | File | Xong khi |
|---|---|---|
| Cài đặt `resize`, `denoise`, `equalize` | `backend/image_processing/preprocessing.py` | `preprocess()` chạy được trên ảnh PlantVillage, trả ảnh `(512, 512, 3)` `uint8` |
| Test cho tiền xử lý | `backend/image_processing/tests/test_preprocessing.py` | Kiểm tra kích thước, kiểu dữ liệu, ảnh tối sau CLAHE có độ tương phản kênh L tăng |
| Script chia train/test (80/20, chia đều theo lớp, `random_state` cố định) | `backend/experiments/split_dataset.py` | Tạo `dataset/splits/train.txt`, `test.txt` và commit hai file này |
| Thí nghiệm histogram trước/sau CLAHE, so sánh Bilateral và Median | `backend/experiments/histogram_clahe.py` | Lưu hình vào `backend/experiments/output/`, dùng cho báo cáo |

Ghi chú:
- Ảnh vào là **BGR**: dùng `cv2.COLOR_BGR2LAB`, không dùng `RGB2LAB`.
- Tham số đặt sẵn ở đầu file. Muốn đổi thì sửa hằng số, không viết số trực tiếp trong hàm.
- Tuần 3: viết `backend/experiments/evaluate.py`, tính IoU của mask so với mask tô tay, sai số S%, và tỷ lệ xếp đúng cấp 0–4.

---

## 2. Thành viên 2: tách lá, tách đốm bệnh, hình thái học

**Nhánh:** `tv2/tach-la-va-dom-benh` · **Người review:** Thành viên 3

| Việc | File | Xong khi |
|---|---|---|
| `segment_leaf`: HSV, Otsu trên kênh S, closing, lấp lỗ | `backend/image_processing/segmentation.py` | Mask lá gồm **cả vết bệnh**, trả đủ ảnh `saturation`, `leaf_mask` |
| `segment_lesions`: ROI, mask mô khỏe theo Hue 35–85, lá trừ mô khỏe, opening rồi closing | như trên | `lesion_mask` nằm trọn trong `leaf_mask`, trả đủ 4 ảnh trung gian |
| `measure_lesions`, `draw_lesions` | như trên | Mỗi đốm có `area`, `perimeter`, `circularity`, `center`, `bbox`; ảnh kết quả có viền đỏ |
| Test bằng ảnh tổng hợp | `backend/image_processing/tests/test_segmentation.py` | Ví dụ hình tròn xanh trên nền trắng có 3 chấm nâu → diện tích lá sai lệch không quá 2%, đếm đúng 3 đốm |
| Tô tay mask cho khoảng 30 ảnh test | `backend/dataset/masks/` (chia sẻ ngoài git) | Đủ mask lá và mask vết bệnh |

Ghi chú:
- Mask chỉ gồm **0 và 255**, kiểu `uint8`. `pipeline.run()` sẽ báo lỗi nếu sai.
- Kênh H của OpenCV chạy **0–179**.
- Chạy thử trên ảnh thật: `python -m image_processing.pipeline <ảnh> --out ket_qua`. Lệnh này cần giai đoạn 1 và 4 chạy được; trong lúc chờ, gọi trực tiếp các hàm của mình trong một script thử.
- Tuần 3: tinh chỉnh ngưỡng và kernel dựa trên IoU với mask tô tay.

---

## 3. Thành viên 3: trích xuất đặc trưng và phân loại

**Nhánh:** `tv3/phan-loai-benh` · **Người review:** Thành viên 4

| Việc | File | Xong khi |
|---|---|---|
| `extract_features`: GLCM (5 thuộc tính × 4 góc) trên ảnh xám, Color Moments (mean, std, skewness) trên H, S, V, chỉ tính trong vùng lá | `backend/image_processing/classifier.py` | Vector có độ dài cố định, cùng một ảnh luôn cho cùng kết quả |
| Script huấn luyện: đọc `splits/train.txt`, lấy đặc trưng, `StandardScaler` + SVM (`probability=True`), lưu model | `backend/image_processing/train_classifier.py` | Có file `image_processing/models/classifier.joblib`, nhãn trùng `diseases.code` |
| Đánh giá trên `splits/test.txt`: classification report, confusion matrix | như trên, lưu hình vào `backend/experiments/output/` | Bảng F1 từng lớp cho báo cáo |
| Test cho đặc trưng | `backend/image_processing/tests/test_classifier.py` | Độ dài vector đúng, không lỗi với ảnh tổng hợp |

Ghi chú:
- Ảnh huấn luyện phải đi qua **đúng** `preprocess()` và `segment_leaf()` như lúc chạy thật, nếu không đặc trưng sẽ lệch.
- Trong lúc Thành viên 2 chưa xong `segment_leaf`: ảnh PlantVillage có nền đồng nhất, nên tạm dùng một ngưỡng đơn giản để có mask lá. Khi có bản thật thì **huấn luyện lại**.
- `predict()` đã viết sẵn, không cần sửa.
- Tuần 3: so sánh SVM với Random Forest. Nếu kịp, chạy thêm MobileNetV2 trong một notebook riêng, không đưa vào web.

---

## 4. Thành viên 4: backend API, giao diện, tích hợp

Mỗi việc một nhánh nhỏ. **Người review:** Thành viên 1.

| Nhánh | Việc | Xong khi |
|---|---|---|
| `tv4/nap-lop-benh` | Data migration nạp các lớp đã chốt vào `diseases` (tên tiếng Việt, mô tả) | `migrate` xong là bảng có đủ dữ liệu |
| `tv4/api-chan-doan` | `POST /api/diagnoses/` (tải ảnh → chạy `pipeline.run()` → lưu kết quả và `diagnosis_steps`), `GET` danh sách và chi tiết (chỉ của chính mình), `PATCH` bookmark | Trả đúng dữ liệu ghi trong `frontend/src/api/diagnoses.js`; `PipelineError` → `failed` kèm thông báo; test thay `pipeline.run` bằng kết quả giả |
| `tv4/dang-ky` | API đăng ký có ô đồng ý điều khoản, trang đăng ký trên frontend | Tạo được tài khoản mới và đăng nhập ngay |
| `tv4/phan-hoi-bao-loi` | API và giao diện gửi phản hồi về kết quả sai, báo lỗi ứng dụng | Admin thấy được trong `/admin/` |
| `tv4/docker` (tuần 4) | Docker Compose: postgres, backend, frontend | Chạy được `docker compose up` trên máy khác |

Ghi chú:
- Không cần chờ các giai đoạn 1–4: viết API với `pipeline.run` được thay bằng hàm giả, như cách `image_processing/tests/test_pipeline.py` đang làm.
- Giới hạn kích thước ảnh tải lên (ví dụ 10 MB) và chỉ nhận JPG/PNG.
- Đổi `disease_code` sang `disease_id` bằng `Disease.objects.get(code=...)`. Mã lạ (model và bảng không khớp) phải báo lỗi rõ ràng.

---

## 5. Quy trình Git

### Quy tắc
- **Không push thẳng lên `main`**: nhánh được bảo vệ, chỉ merge qua PR, cần CI xanh và **1 người duyệt**.
- Tên nhánh: `tvX/mo-ta-ngan`, viết thường, không dấu, nối bằng gạch ngang. Ví dụ: `tv2/tach-la-va-dom-benh`.
- Commit: `loai(phan): mô tả`.
  - `loai`: `feat` (tính năng), `fix` (sửa lỗi), `test`, `docs`, `refactor`, `chore`.
  - `phan`: `preprocessing`, `segmentation`, `classifier`, `pipeline`, `api`, `frontend`, `db`, `experiments`.
  - Ví dụ: `feat(segmentation): tách lá bằng Otsu trên kênh S`
- Mỗi PR một việc, càng nhỏ càng dễ duyệt. PR được **squash merge**, rồi xóa nhánh.
- Chỉ sửa file thuộc phần mình. Muốn đổi quy ước chung (`pipeline.py`, `steps.py`, `docs/pipeline.md`, models) thì báo cả nhóm trước.
- Không commit: ảnh trong `dataset/` (trừ `splits/*.txt`), file `.env`, file model (khi nhóm chưa chốt).

### Các lệnh

```powershell
# 1. Bắt đầu một việc mới: luôn tách từ main mới nhất
git switch main
git pull
git switch -c tv2/tach-la-va-dom-benh

# 2. Làm việc, commit thường xuyên
git add backend/image_processing/segmentation.py backend/image_processing/tests/test_segmentation.py
git commit -m "feat(segmentation): tách lá bằng Otsu trên kênh S"

# 3. Chạy kiểm tra giống CI trước khi push (trong backend/, đã kích hoạt venv)
python manage.py test api image_processing
#    và nếu có sửa frontend (trong frontend/):  npm run lint ; npm run build

# 4. Push nhánh lên GitHub
git push -u origin tv2/tach-la-va-dom-benh   # lần đầu
git push                                     # các lần sau

# 5. Mở PR trên GitHub vào main, chọn người review theo bảng ở trên

# 6. Khi main có thay đổi mới (ví dụ PR của người khác vừa merge)
git fetch origin
git merge origin/main
#    sửa xung đột nếu có, chạy lại test, rồi git push

# 7. Sau khi PR được merge: quay về main, xóa nhánh cũ ở máy
git switch main
git pull
git branch -d tv2/tach-la-va-dom-benh
```

### Khi review PR của người khác
- Kéo nhánh về chạy thử: `git fetch origin` rồi `git switch tv1/tien-xu-ly`.
- Kiểm tra: đúng quy ước trong `docs/pipeline.md`, có test, CI xanh, không commit ảnh hay `.env`.
- Góp ý bằng comment trên PR. Duyệt bằng **Approve**; cần sửa thì chọn **Request changes**.

---

## 6. Mốc thời gian

| Tuần | Thành viên 1 | Thành viên 2 | Thành viên 3 | Thành viên 4 |
|---|---|---|---|---|
| 2 | Tiền xử lý, chia train/test, histogram | Tách lá, tách đốm, tô tay mask | Đặc trưng, huấn luyện bản đầu | Nạp lớp bệnh, API chẩn đoán, đăng ký |
| 3 | `evaluate.py`, số liệu tiền xử lý | Tinh chỉnh ngưỡng theo IoU | So sánh SVM / RF, huấn luyện lại | Ghép pipeline thật, phản hồi, báo lỗi |
| 4 | Báo cáo phần 1 | Báo cáo phần 2–3 | Báo cáo phần 4 | Docker, demo, slide chung |
