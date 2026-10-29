# Image backend: Django + pipeline xử lý ảnh + model classifier.joblib, chạy bằng gunicorn.
# Build qua docker-compose.yml ở thư mục gốc. Không chứa dataset/ và media/ (xem .dockerignore).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# opencv-python cần libGL và glib
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài thư viện trước khi chép code: sửa code không phải cài lại
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Bản đóng gói bắt buộc có model phân loại; thiếu thì dừng build ngay
RUN test -f image_processing/models/classifier.joblib

EXPOSE 8000

# Khởi động: migrate -> collectstatic (cho trang /admin/) -> tạo admin nếu có cấu hình -> gunicorn.
# Timeout 120 s vì POST /api/diagnoses/ chạy pipeline ngay trong request.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && if [ -n \"$DJANGO_SUPERUSER_EMAIL\" ]; then python manage.py createsuperuser --noinput || echo 'Tài khoản quản trị đã có, bỏ qua'; fi && exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120 --access-logfile -"]
