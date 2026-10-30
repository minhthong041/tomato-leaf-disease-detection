# Hệ thống phát hiện, phân loại và đo lường mức độ nghiêm trọng của bệnh trên lá cà chua dựa trên xử lý ảnh số

Đồ án môn **Xử lý ảnh số**: người dùng tải lên ảnh **một chiếc lá cà chua**, hệ thống tách lá khỏi nền, tìm các vết bệnh, tính **tỷ lệ diện tích lá bị bệnh**, xếp **cấp độ 0–4** kèm khuyến nghị xử lý theo IPM (quản lý dịch hại tổng hợp), và nhận diện **tên bệnh**. Giao diện web hiển thị ảnh qua từng bước xử lý.

Phạm vi chính thức: [docs/TongQuanDuAn.md](docs/TongQuanDuAn.md).

## Mục tiêu

| Giai đoạn | Cách làm | Kết quả |
|---|---|---|
| 1. Tiền xử lý | Resize 512×512, khử nhiễu Bilateral / Median, CLAHE trên kênh L của CIELAB | Ảnh chuẩn hóa |
| 2. Tách lá khỏi nền | HSV, ngưỡng Hue/Saturation, closing 5×5 một lần, tô contour ngoài lớn nhất | Mask lá, diện tích lá |
| 3. Tách đốm bệnh | Mô khỏe theo Hue (35–85), lọc đốm theo Saturation/Value, hình thái học và diện tích pixel | Mask vết bệnh, diện tích và thông số từng đốm |
| 4. Phân loại tên bệnh | Đặc trưng GLCM + Color Moments, SVM / Random Forest (PlantVillage, lá cà chua) | Tên bệnh, độ tin cậy |
| 5. Mức độ nghiêm trọng | S = diện tích bệnh / diện tích lá × 100% | Cấp 0–4, khuyến nghị IPM |

```
Ảnh lá ─► Tiền xử lý ─► Tách lá ─► Tách đốm bệnh ─► Contours ─► S (%) ─► Cấp 0–4 + khuyến nghị
                                 └──────────────► Đặc trưng ─► SVM / RF ─► Tên bệnh
```

## Trạng thái

| Phần | Trạng thái |
|---|---|
| Database (PostgreSQL) và model Django | Xong |
| Trang quản trị `/admin/` | Xong |
| Docker Compose | Xong — `docker compose up` chạy db, backend, frontend; mở http://localhost:8080 |
| Đăng nhập JWT, CORS cho frontend | Xong |
| Đăng ký tài khoản, trang điều khoản sử dụng | Xong — `POST /api/auth/register/` (đăng nhập luôn), trang `/register`, `/terms` |
| Xóa tài khoản | Xong — `POST /api/auth/delete-account/` (nhập lại mật khẩu, ẩn danh hóa, thu hồi token), trang `/account` |
| Khung pipeline và quy ước vào/ra ([docs/pipeline.md](docs/pipeline.md)) | Xong |
| Chia dữ liệu train/test | Xong — 80/20 theo từng lớp ([experiments/split_dataset.py](backend/experiments/split_dataset.py), `dataset/splits/*.txt`); tên thư mục lớp phải trùng `diseases.code` |
| Giai đoạn 1: tiền xử lý (resize, Bilateral, CLAHE) | Xong |
| Giai đoạn 2–3: tách lá, tách đốm bệnh | Xong bản đầu, ngưỡng đốm bệnh còn tạm thời |
| Giai đoạn 4: trích đặc trưng GLCM + Color Moments | Xong |
| Giai đoạn 4: huấn luyện SVM / Random Forest | Xong (3E) — so sánh trên cùng đặc trưng của 3C, chọn SVM (C=1000, gamma=0,03): accuracy 0,893, macro F1 0,859; Random Forest: 0,843 / 0,798 |
| Cấp độ 0–4 và khuyến nghị IPM | Xong |
| Khuyến nghị theo từng bệnh | Xong — nội dung 3D trong `backend/api/recommendations.py` (khóa theo `diseases.code`), API trả `disease_recommendation`; trang kết quả hiện cả khuyến nghị theo cấp và theo bệnh (bệnh virus, nhện đỏ, lá khỏe chỉ hiện theo bệnh) |
| Danh sách lớp bệnh (bảng `diseases`) | Xong — đủ 10 lớp lá cà chua của PlantVillage, nạp bằng migration |
| API tải ảnh, lịch sử, kết quả, đánh dấu | Xong — chạy pipeline ngay trong request, trả `done` hoặc `failed` (ảnh không chẩn đoán được hoặc lỗi hệ thống); lọc đã lưu bằng `?is_bookmarked=true` |
| Phản hồi kết quả sai, báo lỗi | Xong — `POST /api/feedbacks/`, `POST /api/error-reports/`; nút "Báo kết quả sai" trên trang kết quả, trang `/error-report`; quản trị viên xử lý trong `/admin/` |
| Cảnh báo kết quả đáng ngờ | Xong — trang kết quả cảnh báo khi độ tin cậy dưới 60% (3E đề xuất 0,55, chờ cập nhật ở frontend) hoặc tên bệnh mâu thuẫn với cấp độ, gợi ý gửi phản hồi |
| Giao diện frontend | Có khung: đăng nhập, đăng ký, điều khoản, tải ảnh, kết quả (lưu / bỏ lưu), lịch sử (lọc đã lưu), phản hồi, báo lỗi — đã nối API |

## Công nghệ

- **Backend:** Python 3.12, Django 6.1, Django REST Framework, SimpleJWT, PostgreSQL (psycopg 3)
- **Xử lý ảnh và phân loại:** OpenCV, NumPy, scikit-image, scikit-learn, SciPy, Matplotlib
- **Frontend:** React 19, Vite 8, MUI 9 (Material UI), React Router 7

## Cấu trúc thư mục

```
tomato-leaf-disease-detection/
├── backend/
│   ├── core/                 # settings, urls của Django
│   ├── api/                  # model, admin, API, lưu ảnh (images.py)
│   ├── image_processing/     # pipeline xử lý ảnh, xem docs/pipeline.md
│   │   ├── preprocessing.py  #   giai đoạn 1 — Thành viên 1
│   │   ├── segmentation.py   #   giai đoạn 2, 3 — Thành viên 2
│   │   ├── classifier.py     #   giai đoạn 4 — Thành viên 3
│   │   ├── severity.py       #   giai đoạn 5: cấp độ, khuyến nghị IPM
│   │   ├── pipeline.py       #   ghép các giai đoạn, chạy thử một ảnh
│   │   └── models/           #   file model phân loại (.joblib)
│   ├── dataset/              # ảnh PlantVillage, mask tô tay, ảnh tự chụp — không đưa lên git (trừ splits/*.txt)
│   ├── experiments/          # script thí nghiệm, đánh giá, xem segmentation; output/ không đưa lên git
│   ├── media/                # ảnh tải lên (uploads/), ảnh kết quả (results/), ảnh từng bước (steps/) — không đưa lên git
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/api/              # gọi backend, tự refresh token
│   ├── src/auth/             # trạng thái đăng nhập, chặn trang khi chưa đăng nhập
│   ├── src/pages/            # các trang
│   ├── src/components/       # Layout, thanh đo cấp độ, ảnh từng bước
│   └── .env.example
└── docs/
    ├── TongQuanDuAn.md       # phạm vi, kỹ thuật, phân công (tài liệu chính)
    ├── pipeline.md           # quy ước vào/ra giữa các module xử lý ảnh
    ├── leaf-disease-db.md    # schema xuất từ DrawSQL (nguồn chuẩn)
    └── database.md           # giải thích database cho cả nhóm
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
- Image backend có sẵn model `classifier.joblib`, không chứa `dataset/`.

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

Frontend chạy ở http://localhost:5173. Chưa đăng nhập thì mọi trang chuyển về `/login`; tài khoản tạo bằng `createsuperuser` hoặc trong `/admin/`.

### Sau khi kéo code mới

```powershell
pip install -r requirements.txt   # trong backend/, khi requirements.txt thay đổi
python manage.py migrate          # khi có migration mới
npm install                       # trong frontend/, khi package.json thay đổi
```

## API hiện có

| Phương thức | Đường dẫn | Gửi lên | Trả về |
|---|---|---|---|
| POST | `/api/auth/login/` | `{"email", "password"}` | `{"access", "refresh"}` |
| POST | `/api/auth/refresh/` | `{"refresh"}` | Cặp token mới (refresh cũ bị vô hiệu) |
| POST | `/api/auth/logout/` | `{"refresh"}` | Vô hiệu refresh token |
| POST | `/api/auth/delete-account/` | `{"password"}` | 204; xóa tài khoản của chính mình (ẩn danh hóa, thu hồi mọi refresh token). Sai mật khẩu, hoặc tài khoản quản trị (phải xóa trong `/admin/`), trả 400 |
| POST | `/api/diagnoses/` | multipart, trường `image` (JPG/PNG, tối đa 10 MB) | Kết quả chẩn đoán, trạng thái `done` hoặc `failed` |
| GET | `/api/diagnoses/` | | Lịch sử của người đang đăng nhập, mới nhất trước, 20 mục/trang |
| GET | `/api/diagnoses/:id/` | | Chi tiết một lần chẩn đoán (ảnh từng bước, khuyến nghị IPM) |
| PATCH | `/api/diagnoses/:id/` | `{"is_bookmarked"}` | Lần chẩn đoán sau khi đánh dấu |

Cấu trúc dữ liệu trả về: [frontend/src/api/diagnoses.js](frontend/src/api/diagnoses.js). Mỗi người chỉ xem được lần chẩn đoán của mình (của người khác trả 404).

Các API khác yêu cầu header `Authorization: Bearer <access token>`. Access token hết hạn sau 30 phút, refresh token sau 7 ngày.

## Lệnh hay dùng

```powershell
python manage.py makemigrations api   # sau khi sửa models.py
python manage.py migrate
python manage.py check
python manage.py test api image_processing experiments   # chạy test
python experiments/evaluate.py   # đánh giá tách lá, vết bệnh, cấp độ trên 30 ảnh mask chuẩn
python -m image_processing.pipeline anh.jpg --out ket_qua   # chạy pipeline trên một ảnh
npm run lint                          # kiểm tra code frontend
```

## Lưu ý cho thành viên

- **Database:** đọc [docs/database.md](docs/database.md) trước khi sửa model. Khi đổi schema, cập nhật cả diagram DrawSQL, `docs/leaf-disease-db.md` và `docs/database.md`.
- **Migration:** chỉ thêm migration mới, không sửa hay xóa migration đã có trên git.
- **Ảnh không đưa lên git:** nội dung `dataset/` và `media/` bị bỏ qua (chỉ giữ file `.gitkeep`). Bộ ảnh thử của nhóm được chia sẻ riêng.
- **Thêm thư viện Python:** cập nhật `requirements.txt` bằng `pip freeze | Out-File -Encoding utf8 requirements.txt`. **Đừng dùng `pip freeze > requirements.txt`** trong Windows PowerShell: lệnh đó ghi file dạng UTF-16, GitHub sẽ không xem được nội dung file.
- **Pipeline:** đọc [docs/pipeline.md](docs/pipeline.md) trước khi viết module xử lý ảnh — kiểu dữ liệu vào/ra, tên ảnh trung gian, các quy tắc `pipeline.run()` kiểm tra.
- **OpenCV:** ảnh được đọc theo thứ tự BGR (dùng `cv2.COLOR_BGR2HSV`), và kênh H chạy 0–179 chứ không phải 0–359. Đọc ảnh bằng `pipeline.load_image()` thay cho `cv2.imread()` để không lỗi với đường dẫn có dấu tiếng Việt.
