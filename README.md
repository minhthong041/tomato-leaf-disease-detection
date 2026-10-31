# Hệ thống phát hiện, phân loại và đo lường mức độ nghiêm trọng của bệnh trên lá cà chua dựa trên xử lý ảnh số

Đồ án môn **Xử lý ảnh** (Học viện Công nghệ Bưu chính Viễn thông, giảng viên hướng dẫn: Đỗ Đức Hào). Người dùng tải lên ảnh **một chiếc lá cà chua**; hệ thống tách lá khỏi nền, tìm các vết bệnh, tính **tỷ lệ diện tích lá bị bệnh S**, xếp **cấp độ 0–4** kèm khuyến nghị xử lý theo IPM (quản lý dịch hại tổng hợp) và nhận diện **tên bệnh** trong 10 lớp lá cà chua của PlantVillage. Giao diện web hiển thị ảnh qua từng bước xử lý.

Phạm vi chính thức: [docs/TongQuanDuAn.md](docs/TongQuanDuAn.md).

## Nhóm thực hiện

| Thành viên | Phụ trách |
|---|---|
| Cao Minh Thông (trưởng nhóm) | Dữ liệu, tiền xử lý, đánh giá và thí nghiệm, tinh chỉnh tách vết bệnh, giao diện web, báo cáo |
| Nguyễn Quốc Dương | Tách lá, tách vết bệnh và hình thái học |
| Đỗ Thị Thanh Thủy | Trích đặc trưng và phân loại, khuyến nghị theo bệnh |
| Hồ A Nhật Lưu | Backend API, frontend, Docker, demo |

## Pipeline xử lý ảnh

| Giai đoạn | Cách làm | Kết quả |
|---|---|---|
| 1. Tiền xử lý | Resize 512×512 (`INTER_AREA` khi thu nhỏ, `INTER_CUBIC` khi phóng to), lọc song phương (d = 9, σ = 75), CLAHE (clip 2,0, lưới 8×8) trên kênh L* của CIELAB | Ảnh chuẩn hóa |
| 2. Tách lá khỏi nền | Hạt giống màu xanh trong HSV, GrabCut 5 vòng, khôi phục mép lá hoại tử, closing 5×5, tô contour ngoài lớn nhất | Mặt nạ lá, diện tích lá |
| 3. Tách vết bệnh | So màu CIELAB với mô xanh khỏe của chính chiếc lá, loại bóng đổ sát mép, opening rồi closing 5×5, bỏ thành phần nhỏ hơn 40 điểm ảnh | Mặt nạ vết bệnh, số đo từng đốm (diện tích, chu vi, độ tròn, tâm, khung bao) |
| 4. Phân loại tên bệnh | 14 đặc trưng trên vùng lá: 5 đặc trưng GLCM + 9 mô men màu HSV; SVM nhân RBF (C = 1000, γ = 0,03) | Tên bệnh, độ tin cậy |
| 5. Mức độ nghiêm trọng | S = A<sub>lesion</sub> / A<sub>leaf</sub> × 100% | Cấp 0–4, khuyến nghị IPM và khuyến nghị theo từng bệnh |

```
Ảnh lá ─► Tiền xử lý ─► Tách lá ─► Tách vết bệnh ─► Contours ─► S (%) ─► Cấp 0–4 + khuyến nghị
                           └── ảnh + mặt nạ lá ─► Đặc trưng ─► SVM ─► Tên bệnh + độ tin cậy
```

| Cấp | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| S | 0% | 0% < S < 5% | 5% ≤ S < 15% | 15% ≤ S ≤ 35% | S > 35% |
| Mức độ | Khỏe mạnh | Nhiễm nhẹ | Trung bình (ngưỡng hành động IPM) | Nặng | Nguy kịch |

Quy ước vào/ra giữa các module: [docs/pipeline.md](docs/pipeline.md).

## Kết quả chính

**Dữ liệu:** 10 lớp lá cà chua PlantVillage, 18.160 ảnh, chia 80/20 theo từng lớp (14.528 ảnh huấn luyện, 3.632 ảnh kiểm thử); 30 ảnh (3 ảnh mỗi lớp) có mặt nạ lá và mặt nạ vết bệnh tô tay để đánh giá phân đoạn.

| Phân đoạn và xếp cấp (30 ảnh mặt nạ chuẩn) | Kết quả |
|---|---|
| IoU mặt nạ lá | 0,892 |
| IoU / Dice mặt nạ vết bệnh | 0,216 / 0,320 |
| Sai số tuyệt đối trung bình của S | 6,54 điểm % |
| Đúng cấp (21 ảnh có vết bệnh) | 12/21 |
| Lệch không quá 1 cấp (21 ảnh có vết bệnh) | 19/21 |
| Báo nhầm vết bệnh (9 ảnh không có vết bệnh) | 6/9 |

| Phân loại (3.632 ảnh kiểm thử) | Accuracy | Macro F1 |
|---|---|---|
| SVM (C = 1000, γ = 0,03), mô hình được chọn | 0,893 | 0,859 |
| Random Forest | 0,843 | 0,798 |

- **Ngưỡng độ tin cậy 0,55:** cảnh báo 12,2% số ảnh, bắt được 55,7% số dự đoán sai; accuracy trên các ảnh không bị cảnh báo là 94,6%.
- **Thí nghiệm loại bỏ tiền xử lý:** bỏ CLAHE, thay Bilateral bằng Median hay bỏ lọc nhiễu đều không làm phân loại khác có ý nghĩa thống kê (kiểm định McNemar, gần nhất là bỏ CLAHE với p = 0,080); IoU vết bệnh chỉ dao động 0,213–0,217. Hệ thống giữ Bilateral + CLAHE.
- **Thời gian:** khoảng 1–3 giây cho một ảnh, trong đó GrabCut chiếm khoảng 93%.
- **Giới hạn:** chỉ dùng cho ảnh một lá trên nền đơn sắc; ảnh chụp ngoài đồng ruộng có nhiều lá chồng nhau cho kết quả sai.

Chi tiết: [docs/GiaiDoan2_3.md](docs/GiaiDoan2_3.md) (tách lá, tách vết bệnh), [docs/chuong-web.md](docs/chuong-web.md) (ứng dụng web).

## Ứng dụng web

- **Đăng ký, đăng nhập** (JWT, đồng ý điều khoản sử dụng), **xóa tài khoản** (ẩn danh hóa, giữ lịch sử chẩn đoán).
- **Tải ảnh** JPG/PNG tối đa 10 MB: hướng dẫn chụp, nút chụp ảnh trên điện thoại, cảnh báo ảnh quá nhỏ hoặc quá dài.
- **Trang kết quả:** tên bệnh, độ tin cậy, tỷ lệ S, số đốm, thanh đo 5 cấp; cảnh báo khi độ tin cậy dưới 0,55 hoặc tên bệnh mâu thuẫn với cấp độ; so sánh ảnh trước/sau; lớp phủ mặt nạ lá, mặt nạ vết bệnh và khung từng đốm; bảng số đo từng đốm; 9 ảnh trung gian; histogram độ sáng trước và sau CLAHE; khuyến nghị theo cấp và theo từng bệnh; in hoặc lưu PDF.
- **Lịch sử** chẩn đoán, lưu kết quả và lọc "Đã lưu", **báo kết quả sai**, **báo lỗi** ứng dụng.
- **Trang quản trị** `/admin/`: quản lý người dùng, lịch sử, duyệt phản hồi và báo lỗi.

Kịch bản demo: [docs/demo.md](docs/demo.md).

## Công nghệ

- **Xử lý ảnh và phân loại:** Python 3.12, OpenCV, NumPy, scikit-image, scikit-learn, SciPy, Matplotlib
- **Backend:** Django 6.1, Django REST Framework, SimpleJWT, PostgreSQL (psycopg 3; Docker dùng PostgreSQL 17)
- **Frontend:** React 19, Vite 8, MUI 9 (Material UI), React Router 7
- **Triển khai và kiểm thử:** Docker Compose, nginx, gunicorn; 259 kiểm thử tự động, GitHub Actions chạy kiểm thử, lint và build cho mỗi pull request

## Cấu trúc thư mục

```
tomato-leaf-disease-detection/
├── backend/
│   ├── core/                    # settings, urls của Django
│   ├── api/                     # model, admin, API, lưu ảnh (images.py), khuyến nghị theo bệnh (recommendations.py)
│   ├── image_processing/        # pipeline xử lý ảnh, không phụ thuộc Django (xem docs/pipeline.md)
│   │   ├── preprocessing.py     #   giai đoạn 1: resize, Bilateral, CLAHE
│   │   ├── segmentation.py      #   giai đoạn 2, 3: tách lá, tách vết bệnh, đo và vẽ đốm
│   │   ├── classifier.py        #   giai đoạn 4: đặc trưng GLCM + mô men màu, dự đoán
│   │   ├── train_classifier.py  #   huấn luyện, so sánh SVM với Random Forest
│   │   ├── severity.py          #   giai đoạn 5: cấp độ, khuyến nghị IPM
│   │   ├── pipeline.py          #   ghép các giai đoạn, chạy thử một ảnh
│   │   └── models/              #   mô hình đã huấn luyện (classifier.joblib)
│   ├── experiments/             # chia dữ liệu, đánh giá, thí nghiệm loại bỏ, vẽ hình; output/ không đưa lên git
│   ├── dataset/                 # ảnh PlantVillage, mặt nạ tô tay — không đưa lên git (trừ splits/*.txt)
│   ├── media/                   # ảnh tải lên, ảnh kết quả, ảnh từng bước — không đưa lên git
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/api/                 # gọi backend, tự làm mới token
│   ├── src/auth/                # trạng thái đăng nhập, chặn trang khi chưa đăng nhập
│   ├── src/pages/               # các trang
│   ├── src/components/          # Layout, thanh đo cấp độ, khung xem ảnh, bảng đốm, histogram CLAHE
│   └── .env.example
├── docs/
│   ├── TongQuanDuAn.md          # phạm vi, kỹ thuật, phân công (tài liệu chính)
│   ├── pipeline.md              # quy ước vào/ra giữa các module xử lý ảnh
│   ├── GiaiDoan2_3.md           # chương tách lá, tách vết bệnh
│   ├── chuong-web.md            # chương ứng dụng web
│   ├── demo.md                  # kịch bản demo
│   ├── leaf-disease-db.md       # schema xuất từ DrawSQL (nguồn chuẩn)
│   └── database.md              # giải thích database cho cả nhóm
├── docker-compose.yml
└── .env.example
```

## Chạy nhanh bằng Docker

Cần Docker Desktop (Windows, macOS) hoặc Docker Engine + Compose v2 (Linux). Từ thư mục gốc repo:

```powershell
docker compose up
```

Lần đầu Docker sẽ build image (vài phút). Xong thì mở **http://localhost:8080**, bấm **Đăng ký** để tạo tài khoản rồi tải ảnh lá lên chẩn đoán.

- 3 dịch vụ: `db` (PostgreSQL), `backend` (Django + gunicorn, tự chạy `migrate` khi khởi động), `frontend` (nginx phục vụ giao diện, chuyển `/api`, `/admin` tới backend). Cấu hình: [docker-compose.yml](docker-compose.yml).
- Dữ liệu database và ảnh tải lên nằm trong volume `postgres-data`, `media`: tắt rồi bật lại vẫn còn.
- Biến môi trường đọc từ `.env` ở thư mục gốc (mẫu: [.env.example](.env.example)). Không có `.env` thì dùng giá trị mặc định, **chỉ để chạy thử trên máy**: khi đưa lên server phải đặt `DB_PASSWORD`, `DJANGO_SECRET_KEY` mới.
- Image backend có sẵn mô hình `classifier.joblib`, không chứa `dataset/`.

```powershell
docker compose up -d                                           # chạy nền
docker compose logs -f backend                                 # xem log backend
docker compose exec backend python manage.py createsuperuser   # tạo tài khoản quản trị (/admin/)
docker compose up --build                                      # build lại sau khi kéo code mới
docker compose down                                            # tắt (giữ dữ liệu)
docker compose down -v                                         # tắt và XÓA database, ảnh tải lên
```

Hoặc đặt `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` trong `.env` để tài khoản quản trị được tạo tự động lúc khởi động.

## Cài đặt để phát triển

### Yêu cầu
- Python 3.12
- PostgreSQL đang chạy trên máy
- Node.js 20.19+ hoặc 22.12+ (yêu cầu của Vite)

### Backend

Các lệnh dưới đây chạy trong PowerShell, từ thư mục `backend/`.

```powershell
# 1. Môi trường ảo và thư viện
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Cấu hình
Copy-Item .env.example .env
```

Mở `.env` và điền:
- `DB_PASSWORD`: mật khẩu user PostgreSQL trên máy bạn.
- `DJANGO_SECRET_KEY`: tạo bằng lệnh
  ```powershell
  python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
  ```

```powershell
# 3. Tạo database (hoặc tạo bằng pgAdmin)
psql -U postgres -c "CREATE DATABASE tomato_leaf_disease_db;"

# 4. Tạo bảng và tài khoản quản trị
python manage.py migrate
python manage.py createsuperuser

# 5. Chạy server
python manage.py runserver
```

Backend chạy ở http://localhost:8000, trang quản trị ở http://localhost:8000/admin/.

### Frontend

Từ thư mục `frontend/`:

```powershell
npm install
Copy-Item .env.example .env   # VITE_API_URL: địa chỉ API backend
npm run dev
```

Frontend chạy ở http://localhost:5173. Chưa đăng nhập thì mọi trang chuyển về `/login`; tạo tài khoản ở trang **Đăng ký** (`/register`).

### Sau khi kéo code mới

```powershell
pip install -r requirements.txt   # trong backend/, khi requirements.txt thay đổi
python manage.py migrate          # khi có migration mới
npm install                       # trong frontend/, khi package.json thay đổi
```

### Dữ liệu cho thí nghiệm

Chạy hệ thống không cần bộ dữ liệu vì mô hình đã có sẵn. Để huấn luyện lại hoặc chạy lại các thí nghiệm, đặt ảnh PlantVillage vào `backend/dataset/plantvillage/<mã lớp>/` (tên thư mục trùng `diseases.code`, ví dụ `Tomato___Early_blight`) và mặt nạ tô tay vào `backend/dataset/masks/`. Danh sách chia train/test và bộ 30 ảnh chuẩn có sẵn trong `backend/dataset/splits/`.

## API

Mọi API trừ đăng ký, đăng nhập và làm mới token yêu cầu header `Authorization: Bearer <access token>`. Access token hết hạn sau 30 phút, refresh token sau 7 ngày.

| Phương thức | Đường dẫn | Gửi lên | Trả về |
|---|---|---|---|
| POST | `/api/auth/register/` | email, họ tên, mật khẩu, đồng ý điều khoản | Tài khoản mới và cặp token (đăng nhập luôn) |
| POST | `/api/auth/login/` | `{"email", "password"}` | `{"access", "refresh"}` |
| POST | `/api/auth/refresh/` | `{"refresh"}` | Cặp token mới (refresh cũ bị vô hiệu) |
| POST | `/api/auth/logout/` | `{"refresh"}` | Vô hiệu refresh token |
| POST | `/api/auth/delete-account/` | `{"password"}` | 204; xóa tài khoản của chính mình (ẩn danh hóa, thu hồi mọi refresh token). Sai mật khẩu, hoặc tài khoản quản trị (phải xóa trong `/admin/`), trả 400 |
| POST | `/api/diagnoses/` | multipart, trường `image` (JPG/PNG, tối đa 10 MB) | Kết quả chẩn đoán, trạng thái `done` hoặc `failed` |
| GET | `/api/diagnoses/` | `?page=`, `?is_bookmarked=true` | Lịch sử của người đang đăng nhập, mới nhất trước, 20 mục/trang |
| GET | `/api/diagnoses/:id/` | | Chi tiết: kết quả, ảnh từng bước, danh sách đốm, khuyến nghị theo cấp và theo bệnh |
| PATCH | `/api/diagnoses/:id/` | `{"is_bookmarked"}` | Lần chẩn đoán sau khi lưu hoặc bỏ lưu |
| POST | `/api/feedbacks/` | mã lần chẩn đoán, tiêu đề, mô tả | Phản hồi kết quả sai |
| POST | `/api/error-reports/` | tiêu đề, mô tả | Báo lỗi ứng dụng |

Cấu trúc dữ liệu trả về: [frontend/src/api/diagnoses.js](frontend/src/api/diagnoses.js). Mỗi người chỉ xem được lần chẩn đoán của mình (của người khác trả 404).

## Lệnh hay dùng

Từ thư mục `backend/` (đã kích hoạt venv):

```powershell
python manage.py test api image_processing experiments     # chạy toàn bộ kiểm thử
python -m image_processing.pipeline anh.jpg --out ket_qua  # chạy pipeline trên một ảnh, lưu ảnh từng bước
python experiments/evaluate.py                             # đánh giá tách lá, vết bệnh, cấp độ trên 30 ảnh mặt nạ chuẩn
python experiments/ablation.py --classify                  # thí nghiệm loại bỏ tiền xử lý (cả phân loại)
python experiments/histogram_clahe.py                      # histogram trước/sau CLAHE, so sánh Bilateral với Median
python experiments/visualize_morphology.py                 # hình minh họa các bước hình thái học
python -m image_processing.train_classifier                # huấn luyện lại, so sánh SVM với Random Forest
python manage.py makemigrations api                        # sau khi sửa models.py
python manage.py migrate
```

Từ thư mục `frontend/`:

```powershell
npm run lint    # kiểm tra code frontend
npm run build   # build bản chạy thật
```

## Lưu ý cho thành viên

- **Database:** đọc [docs/database.md](docs/database.md) trước khi sửa model. Khi đổi schema, cập nhật cả diagram DrawSQL, `docs/leaf-disease-db.md` và `docs/database.md`.
- **Migration:** chỉ thêm migration mới, không sửa hay xóa migration đã có trên git.
- **Ảnh không đưa lên git:** nội dung `dataset/` và `media/` bị bỏ qua (chỉ giữ file `.gitkeep`). Bộ ảnh thử của nhóm được chia sẻ riêng.
- **Thêm thư viện Python:** cập nhật `requirements.txt` bằng `pip freeze | Out-File -Encoding utf8 requirements.txt`. **Đừng dùng `pip freeze > requirements.txt`** trong Windows PowerShell: lệnh đó ghi file dạng UTF-16, GitHub sẽ không xem được nội dung file.
- **Pipeline:** đọc [docs/pipeline.md](docs/pipeline.md) trước khi sửa module xử lý ảnh — kiểu dữ liệu vào/ra, tên ảnh trung gian, các quy tắc `pipeline.run()` kiểm tra.
- **OpenCV:** ảnh được đọc theo thứ tự BGR (dùng `cv2.COLOR_BGR2HSV`), và kênh H chạy 0–179 chứ không phải 0–359. Đọc ảnh bằng `pipeline.load_image()` thay cho `cv2.imread()` để không lỗi với đường dẫn có dấu tiếng Việt.
