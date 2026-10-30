# Cấu trúc Database — Leaf Disease Detection

Tài liệu này mô tả database của backend (Django + PostgreSQL): có những bảng nào, mỗi cột dùng để làm gì, các quy tắc nghiệp vụ mà database đang ép buộc, và những điều cần biết khi viết code đụng tới dữ liệu.

- Schema gốc (xuất từ DrawSQL): [leaf-disease-db.md](leaf-disease-db.md)
- Code model: [backend/api/models.py](../backend/api/models.py)
- Lưu ảnh (tên file, xóa EXIF): [backend/api/images.py](../backend/api/images.py)

> Khi sửa model, hãy cập nhật cả diagram DrawSQL và tài liệu này.

---

## 1. Tổng quan

Phạm vi theo [TongQuanDuAn.md](TongQuanDuAn.md): chỉ xử lý **lá cà chua**. Pipeline xử lý ảnh tách lá, tách vết bệnh và đo tỷ lệ diện tích bệnh để xếp **Cấp 0–4**; bộ phân loại (GLCM + Color Moments → SVM / Random Forest) cho biết **tên bệnh**. Kết quả — tên bệnh, độ tin cậy, diện tích lá, diện tích vết bệnh, tỷ lệ nhiễm, số đốm, chi tiết từng đốm, cấp độ — được lưu trong `diagnosis_histories`; ảnh các bước trung gian lưu trong `diagnosis_steps`.

| Bảng | Model Django | Vai trò |
|---|---|---|
| `users` | `User` | Tài khoản người dùng, đăng nhập bằng email |
| `diseases` | `Disease` | Danh mục lớp bệnh lá cà chua của bộ phân loại (nhãn PlantVillage), kể cả lớp lá khỏe |
| `diagnosis_histories` | `DiagnosisHistory` | Mỗi lần người dùng gửi ảnh, kèm kết quả phân tích |
| `diagnosis_steps` | `DiagnosisStep` | Ảnh trung gian của từng bước pipeline, để giao diện hiển thị |
| `feedbacks` | `Feedback` | Người dùng báo một kết quả phân tích bị sai |
| `error_reports` | `ErrorReport` | Báo lỗi ứng dụng do người dùng gửi |

```mermaid
erDiagram
    users ||--o{ diagnosis_histories : "gửi ảnh"
    users ||--o{ error_reports : "báo lỗi"
    diagnosis_histories ||--o{ feedbacks : "được phản hồi"
    diseases ||--o{ diagnosis_histories : "kết quả phân loại"
    diagnosis_histories ||--o{ diagnosis_steps : "ảnh từng bước"

    users {
        bigint id PK
        varchar email "unique, nullable"
        varchar username "unique, nullable"
        varchar fullname
        boolean is_staff
        timestamptz deleted_at "nullable"
    }
    diagnosis_histories {
        bigint id PK
        bigint user_id FK
        bigint disease_id FK "nullable"
        decimal disease_confidence "nullable"
        varchar status
        smallint severity_level "nullable"
        integer leaf_area_px "nullable"
        integer lesion_area_px "nullable"
        decimal infected_ratio "nullable"
        integer lesion_count "nullable"
        jsonb lesions "nullable"
    }
    diseases {
        bigint id PK
        varchar code "unique"
        varchar name
        boolean is_healthy
    }
    diagnosis_steps {
        bigint id PK
        bigint history_id FK
        varchar step
        varchar image
    }
    feedbacks {
        bigint id PK
        bigint history_id FK
        varchar status
    }
    error_reports {
        bigint id PK
        bigint user_id FK
        boolean is_resolved
    }
```

### Quy ước chung

- **Khóa chính** của mọi bảng là `id` (`bigserial`), cấu hình qua `DEFAULT_AUTO_FIELD = BigAutoField`.
- **Khóa ngoại** đặt tên `<bảng số ít>_id` (`user_id`, `history_id`). Trong Django truy cập qua field không có `_id`: `history.user`, `feedback.history`.
- **Thời gian**: cả 6 bảng đều có `created_at` và `updated_at` kiểu `timestamptz`, lưu giờ UTC (`USE_TZ = True`). Cả hai do Django tự điền, kế thừa từ `TimeStampedModel`; không gán tay.
- **Trạng thái / bước xử lý** lưu dạng chuỗi (`varchar`) khai báo bằng `TextChoices`; **cấp độ bệnh** lưu dạng số (`smallint` 0–4) khai báo bằng `IntegerChoices`. Không có bảng tra cứu riêng cho các giá trị này. Trong code luôn dùng hằng số, ví dụ `DiagnosisHistory.Status.DONE`, `DiagnosisHistory.SeverityLevel.MILD`, không viết `'done'` hay `1` trực tiếp. Riêng **tên bệnh** là bảng `diseases`, vì danh sách lớp do nhóm chốt và có mô tả đi kèm.
- **Ảnh** lưu trên storage (mặc định thư mục `backend/media/`), database chỉ lưu **đường dẫn tương đối** (`varchar(500)`). Lấy URL đầy đủ bằng `history.original_image.url`.

---

## 2. Chi tiết từng bảng

Các cột là NOT NULL trừ khi ghi "có".

### 2.1. `users`

| Cột | Kiểu | Null | Mặc định | Ý nghĩa |
|---|---|---|---|---|
| `id` | bigserial | | | Khóa chính |
| `email` | varchar(255) | có | | Email đăng nhập. Unique, **không phân biệt hoa thường**. NULL chỉ khi tài khoản đã xóa |
| `username` | varchar(50) | có | | Tên hiển thị tùy chọn. Unique, không phân biệt hoa thường |
| `fullname` | varchar(255) | | | Họ tên |
| `password_hash` | varchar(255) | | | Mật khẩu đã băm. Trong Django là field `password`; luôn dùng `user.set_password()`, không gán trực tiếp |
| `is_active` | boolean | | `true` | `false` = không đăng nhập được (bị khóa hoặc đã xóa) |
| `is_staff` | boolean | | `false` | Được vào trang `/admin/` |
| `is_superuser` | boolean | | `false` | Có mọi quyền trong admin |
| `last_login` | timestamptz | có | | Django tự cập nhật khi đăng nhập |
| `deleted_at` | timestamptz | có | | Thời điểm người dùng xóa tài khoản. NULL = tài khoản còn hoạt động |
| `terms_accepted_at` | timestamptz | | | Thời điểm đồng ý điều khoản sử dụng |
| `terms_version` | varchar(20) | | | Phiên bản điều khoản đã đồng ý (lấy từ `settings.TERMS_VERSION`) |
| `created_at`, `updated_at` | timestamptz | | | |

**Phân quyền:** không có cột vai trò. Chỉ có hai loại tài khoản:
- **Người dùng**: `is_staff = false`, dùng các chức năng trong app (chẩn đoán, lịch sử, feedback, báo lỗi).
- **Quản trị viên**: `is_staff = true`, vào được trang `/admin/` để quản lý người dùng, duyệt feedback và xử lý báo lỗi. `is_superuser = true` thì có mọi quyền trong admin.

Ngoài ra Django tự tạo 2 bảng phụ `users_groups` và `users_user_permissions` (từ `PermissionsMixin`) để phân quyền trong admin.

### 2.2. `diseases`

| Cột | Kiểu | Null | Mặc định | Ý nghĩa |
|---|---|---|---|---|
| `id` | bigserial | | | Khóa chính |
| `code` | varchar(100) | | | Nhãn lớp trong PlantVillage, unique, ví dụ `Tomato___Early_blight`. Bộ phân loại trả về nhãn này, backend tra ra dòng tương ứng |
| `name` | varchar(255) | | | Tên tiếng Việt hiển thị cho người dùng, ví dụ "Bệnh đốm vòng" |
| `description` | text | có | | Mô tả triệu chứng |
| `is_healthy` | boolean | | `false` | `true` cho lớp lá khỏe (`Tomato___healthy`). Chỉ được có **một** dòng như vậy |
| `created_at`, `updated_at` | timestamptz | | | |

Bảng có sẵn **đủ 10 lớp lá cà chua của PlantVillage** (9 lớp bệnh / sâu hại + lá khỏe), nạp bằng migration [`0004_seed_diseases`](../backend/api/migrations/0004_seed_diseases.py) — tên tiếng Việt và mô tả triệu chứng nằm trong file đó. Sửa tên hay mô tả thì viết migration mới, không sửa migration đã có. Không xóa được một lớp đã có kết quả chẩn đoán dùng tới (`PROTECT`).

Ba lớp **xoăn vàng lá**, **khảm lá** (virus) và **nhện đỏ** (sâu hại) có triệu chứng lan cả lá chứ không thành đốm riêng, nên S% tính theo diện tích đốm có thể không phản ánh đúng mức độ của các lớp này.

### 2.3. `diagnosis_histories`

| Cột | Kiểu | Null | Mặc định | Ý nghĩa |
|---|---|---|---|---|
| `id` | bigserial | | | Khóa chính |
| `user_id` | bigint FK → `users` | | | Người gửi ảnh |
| `original_image` | varchar(500) | | | Ảnh gốc người dùng tải lên (`media/uploads/`) |
| `processed_image` | varchar(500) | có | | Ảnh gốc đã vẽ đường viền (contours) quanh các vết bệnh (`media/results/`) |
| `status` | varchar(20) | | `pending` | Trạng thái xử lý, xem [mục 4.2](#42-luồng-chẩn-đoán) |
| `error_message` | text | có | | Lý do lỗi khi `status = 'failed'` |
| `disease_id` | bigint FK → `diseases` | có | | **Tên bệnh** do bộ phân loại dự đoán (giai đoạn 4) |
| `disease_confidence` | decimal(5,4) | có | | Xác suất của lớp được dự đoán (`predict_proba`), **từ 0 đến 1** |
| `severity_level` | smallint | có | | **Cấp độ 0–4** theo tỷ lệ diện tích bệnh, xem [mục 3](#3-giá-trị-hợp-lệ-choices) |
| `leaf_area_px` | integer | có | | Diện tích lá (số điểm ảnh trên mask lá) — kết quả bước tách nền |
| `lesion_area_px` | integer | có | | Diện tích vết bệnh (số điểm ảnh trên mask vết bệnh) |
| `infected_ratio` | decimal(5,4) | có | | `lesion_area_px / leaf_area_px`, **từ 0 đến 1** (ví dụ `0.0850`). Hiển thị % thì nhân 100 ở frontend |
| `lesion_count` | integer | có | | Số đốm bệnh tìm được bằng contours |
| `lesions` | jsonb | có | | Chi tiết từng đốm, xem bên dưới |
| `is_bookmarked` | boolean | | `false` | Người dùng đánh dấu lưu lại |
| `created_at`, `updated_at` | timestamptz | | | |

Các cột kết quả (`disease_id` → `lesions`) là NULL khi chưa có kết quả (`pending`, `processing`, `failed`).

`lesions` là danh sách, mỗi phần tử là một đốm bệnh với các thông số lấy từ contour:

```json
[{"area": 412, "perimeter": 88.6, "circularity": 0.66, "center": [215, 140], "bbox": [198, 122, 35, 37]}]
```

| Khóa | Ý nghĩa |
|---|---|
| `area` | Diện tích đốm (điểm ảnh) |
| `perimeter` | Chu vi (`cv2.arcLength`) |
| `circularity` | Độ tròn = 4π·diện tích / chu vi² (1 = tròn hoàn hảo) |
| `center` | Tâm `[x, y]`, tính từ `cv2.moments` |
| `bbox` | Bounding box `[x, y, rộng, cao]` |

Số phần tử của `lesions` phải bằng `lesion_count` (code pipeline đảm bảo, database không kiểm tra).

Những thứ **không** lưu trong database:
- **Khuyến nghị xử lý**: chỉ phụ thuộc vào cấp độ và tên bệnh, nên để thành hằng số và API trả kèm kết quả: khuyến nghị theo cấp (`IPM_RECOMMENDATIONS` trong `backend/image_processing/severity.py`, trường `recommendation`) và khuyến nghị theo bệnh (`DISEASE_RECOMMENDATIONS` trong `backend/api/recommendations.py`, khóa theo `diseases.code`, trường `disease_recommendation`).
- **Vector đặc trưng** (GLCM, Color Moments) và **file trọng số model**: dùng trong lúc phân loại, không cần lưu theo từng lần chẩn đoán.

### 2.4. `diagnosis_steps`

| Cột | Kiểu | Null | Mặc định | Ý nghĩa |
|---|---|---|---|---|
| `id` | bigserial | | | Khóa chính |
| `history_id` | bigint FK → `diagnosis_histories` | | | Lần chẩn đoán |
| `step` | varchar(30) | | | Tên bước, xem [mục 3](#3-giá-trị-hợp-lệ-choices). Mỗi lần chẩn đoán có tối đa một ảnh cho mỗi bước |
| `image` | varchar(500) | | | Ảnh của bước đó (`media/steps/`) |
| `created_at`, `updated_at` | timestamptz | | | |

Pipeline lưu các bước theo đúng thứ tự xử lý, nên `history.steps.all()` (sắp theo `id`) trả về đúng thứ tự để hiển thị. Ảnh cuối cùng (vẽ contours) không nằm ở đây mà ở `diagnosis_histories.processed_image`.

### 2.5. `feedbacks`

| Cột | Kiểu | Null | Mặc định | Ý nghĩa |
|---|---|---|---|---|
| `id` | bigserial | | | Khóa chính |
| `history_id` | bigint FK → `diagnosis_histories` | | | Kết quả phân tích bị báo sai |
| `title` | varchar(255) | | | Tiêu đề |
| `description` | text | | | Mô tả sai ở đâu (ví dụ "lá khỏe nhưng bị kết luận bệnh nặng") |
| `status` | varchar(20) | | `pending` | Trạng thái duyệt |
| `created_at`, `updated_at` | timestamptz | | | |

### 2.6. `error_reports`

| Cột | Kiểu | Null | Mặc định | Ý nghĩa |
|---|---|---|---|---|
| `id` | bigserial | | | Khóa chính |
| `user_id` | bigint FK → `users` | | | Người báo lỗi |
| `title` | varchar(255) | | | Tiêu đề |
| `description` | text | | | Mô tả lỗi |
| `is_resolved` | boolean | | `false` | Đã xử lý chưa |
| `created_at`, `updated_at` | timestamptz | | | |

---

## 3. Giá trị hợp lệ (choices)

| Cột | Giá trị | Hằng số trong code |
|---|---|---|
| `diagnosis_histories.status` | `pending`, `processing`, `done`, `failed` | `DiagnosisHistory.Status.*` |
| `diagnosis_histories.severity_level` | `0`–`4`, xem bảng dưới | `DiagnosisHistory.SeverityLevel.*` |
| `diagnosis_steps.step` | `resized`, `denoised`, `clahe`, `saturation`, `leaf_mask`, `roi`, `healthy_mask`, `lesion_mask_raw`, `lesion_mask` | `DiagnosisStep.Step.*` |
| `feedbacks.status` | `pending`, `accepted`, `rejected` | `Feedback.Status.*` |

Thang cấp độ, với S = `infected_ratio` × 100%:

| Giá trị | Hằng số | Nhãn | Điều kiện |
|---|---|---|---|
| `0` | `HEALTHY` | Cấp 0 - Khỏe mạnh | S = 0% |
| `1` | `MILD` | Cấp 1 - Nhiễm nhẹ | 0% < S < 5% |
| `2` | `MODERATE` | Cấp 2 - Trung bình | 5% ≤ S < 15% |
| `3` | `SEVERE` | Cấp 3 - Nặng | 15% ≤ S ≤ 35% |
| `4` | `CRITICAL` | Cấp 4 - Nguy kịch | S > 35% |

Nhãn tiếng Việt để hiển thị: `obj.get_status_display()`, `history.get_severity_level_display()`, `step.get_step_display()`.

---

## 4. Quy tắc nghiệp vụ

### 4.1. Đăng ký và đăng nhập

- Đăng nhập bằng **email + mật khẩu**. Email được chuyển về chữ thường khi tạo user, và tìm kiếm khi đăng nhập không phân biệt hoa thường — `Foo@Gmail.com` và `foo@gmail.com` là một tài khoản.
- Tạo user **bắt buộc** có `terms_accepted_at` (người dùng tích "Tôi đồng ý" ở màn hình đăng ký). Thiếu thì `User.objects.create_user()` báo lỗi:
  ```python
  User.objects.create_user(
      email, password, fullname=fullname, terms_accepted_at=timezone.now(),
  )  # terms_version tự lấy từ settings.TERMS_VERSION
  ```
- Khi đổi nội dung điều khoản, tăng `TERMS_VERSION` trong `.env`. Có thể so `user.terms_version` với phiên bản hiện hành để yêu cầu đồng ý lại.
- Tài khoản tạo bằng `createsuperuser` hoặc từ trang admin được tự điền `terms_accepted_at` / `terms_version`.

### 4.2. Luồng chẩn đoán

```
pending ──► processing ──► done
                     └───► failed  (ghi error_message)
```

1. Người dùng tải ảnh → tạo bản ghi với `status = pending`, chỉ có `original_image`.
2. Pipeline xử lý ảnh nhận việc → `processing`.
3. Thành công → điền `disease`, `disease_confidence`, `severity_level`, `leaf_area_px`, `lesion_area_px`, `infected_ratio`, `lesion_count`, `lesions`, `processed_image`, lưu ảnh từng bước vào `diagnosis_steps`, chuyển `done`.
4. Lỗi (ví dụ không tách được lá khỏi nền) → điền `error_message`, chuyển `failed`.

Database **không cho phép** `status = 'done'` khi còn thiếu một trong `disease_id`, `disease_confidence`, `severity_level`, `leaf_area_px`, `lesion_area_px`, `infected_ratio`, `lesion_count` — phải gán kết quả trước hoặc cùng lúc với việc chuyển trạng thái.

### 4.3. Ảnh và quyền riêng tư

- Ảnh tải lên được **đổi tên thành UUID** (ví dụ `uploads/2026/10/3f2a…e9.jpg`): đường dẫn không chứa tên file gốc hay ID người dùng.
- Khi lưu `DiagnosisHistory` với ảnh mới, **metadata EXIF bị xóa** (tọa độ GPS, tên thiết bị…), ảnh được xoay đúng chiều trước khi xóa EXIF.
- Theo điều khoản sử dụng, ảnh được **giữ lại ẩn danh**, kể cả sau khi người dùng xóa tài khoản.

### 4.4. Xóa tài khoản = ẩn danh hóa

Tài khoản **không bao giờ bị xóa khỏi database**. Khi người dùng xóa tài khoản, gọi:

```python
user.anonymize()
```

Hàm này: đặt `email`, `username` = NULL; `fullname` = "Người dùng đã xóa"; mật khẩu không dùng được; `is_active`, `is_staff`, `is_superuser` = false; `deleted_at` = thời điểm hiện tại; gỡ group/quyền.

Kết quả:
- Lịch sử chẩn đoán, feedback, báo lỗi **vẫn còn**, nhưng không còn gắn với thông tin cá nhân.
- Email và username được giải phóng → người đó **đăng ký lại được** bằng chính email cũ (thành tài khoản mới).

Để chặn xóa nhầm, các khóa ngoại tới `users` dùng `on_delete=PROTECT`: gọi `user.delete()` khi user đã có dữ liệu sẽ báo lỗi. Trong admin, nút Delete của người dùng bị ẩn, thay bằng action **"Ẩn danh hóa (xóa tài khoản)"**.

Khi truy vấn người dùng còn hoạt động, lọc `deleted_at__isnull=True` (hoặc `is_active=True`).

### 4.5. Hành vi khi xóa (on_delete)

| Khóa ngoại | Khi xóa bản ghi cha |
|---|---|
| `diagnosis_histories.user_id` | `PROTECT` — chặn |
| `error_reports.user_id` | `PROTECT` — chặn |
| `diagnosis_histories.disease_id` | `PROTECT` — không xóa được lớp bệnh đang được dùng |
| `feedbacks.history_id` | `CASCADE` — xóa lịch sử thì xóa luôn feedback của nó |
| `diagnosis_steps.history_id` | `CASCADE` — xóa lịch sử thì xóa luôn ảnh các bước |

---

## 5. Ràng buộc và index

### Ràng buộc trong database

| Tên | Bảng | Nội dung |
|---|---|---|
| `users_active_requires_email` | `users` | Tài khoản chưa xóa (`deleted_at IS NULL`) bắt buộc có email |
| `users_email_ci_unique` | `users` | Unique trên `LOWER(email)` |
| `users_username_ci_unique` | `users` | Unique trên `LOWER(username)` |
| `dh_ratio_between_0_1` | `diagnosis_histories` | `infected_ratio` nằm trong [0, 1] |
| `dh_lesion_within_leaf` | `diagnosis_histories` | `lesion_area_px <= leaf_area_px` |
| `dh_confidence_between_0_1` | `diagnosis_histories` | `disease_confidence` nằm trong [0, 1] |
| `dh_level_between_0_4` | `diagnosis_histories` | `severity_level` nằm trong [0, 4] |
| `dh_level0_iff_no_lesion` | `diagnosis_histories` | Cấp 0 khi và chỉ khi `lesion_area_px = 0`. So trên số điểm ảnh, không so trên `infected_ratio`, vì tỷ lệ làm tròn 4 chữ số có thể ra `0.0000` khi vẫn còn vết bệnh rất nhỏ |
| `dh_done_requires_result` | `diagnosis_histories` | `status = 'done'` thì phải có `disease_id`, `disease_confidence`, `severity_level`, `leaf_area_px`, `lesion_area_px`, `infected_ratio`, `lesion_count` |
| `diseases_one_healthy` | `diseases` | Chỉ một dòng có `is_healthy = true` (unique có điều kiện) |
| `uq_ds_history_step` | `diagnosis_steps` | Unique `(history_id, step)` |
| (tự động) | `diagnosis_histories` | `leaf_area_px`, `lesion_area_px`, `lesion_count`, `severity_level` không âm (`PositiveIntegerField`, `PositiveSmallIntegerField`) |

Vi phạm ràng buộc sẽ ném `IntegrityError` — API nên bắt và trả lỗi 400 thay vì 500.

### Index

| Tên | Bảng | Cột | Phục vụ truy vấn |
|---|---|---|---|
| `idx_dh_user_created` | `diagnosis_histories` | `(user_id, created_at)` | Lịch sử của một người, mới nhất trước |
| `idx_dh_user_bookmarked` | `diagnosis_histories` | `(user_id, is_bookmarked)` | Danh sách đã lưu của một người |
| `idx_er_unresolved` | `error_reports` | `created_at` **WHERE** `is_resolved = false` | Danh sách báo lỗi chưa xử lý |
| `uq_ds_history_step` | `diagnosis_steps` | `(history_id, step)` | Ảnh các bước của một lần chẩn đoán |
| (tự động) | các bảng | `created_at`, `status`, `severity_level`, `diseases.code`, các khóa ngoại | |

---

## 6. Cài đặt và migration

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # điền DB_PASSWORD, DJANGO_SECRET_KEY (cách tạo key ghi trong file)
python manage.py migrate
python manage.py createsuperuser
```

- Sau khi sửa `models.py`: `python manage.py makemigrations api` rồi `python manage.py migrate`, commit kèm file migration.
- Khi `makemigrations` hỏi "Was X renamed to Y?", chỉ trả lời `y` nếu đúng là đổi tên cùng một dữ liệu; cột mới mang ý nghĩa khác thì trả lời `N`.
- Ngoài 6 bảng trên, Django tự tạo các bảng hệ thống (`django_migrations`, `django_session`, `django_admin_log`, `django_content_type`, `auth_group`, `auth_permission`, các bảng `token_blacklist_*`…) — không cần quan tâm khi làm nghiệp vụ.
