"""Giai đoạn 5 — Cấp độ nghiêm trọng và khuyến nghị IPM theo docs/TongQuanDuAn.md.

S = lesion_area_px / leaf_area_px * 100%. Giá trị cấp trùng api.models.DiagnosisHistory.SeverityLevel.
"""

# Khuyến nghị theo cấp, API trả kèm kết quả
IPM_RECOMMENDATIONS = {
    0: 'Lá khỏe mạnh. Duy trì chăm sóc định kỳ.',
    1: 'Nhiễm nhẹ. Cắt tỉa lá bệnh, phun phòng chế phẩm sinh học (Trichoderma).',
    2: 'Nhiễm trung bình, đã tới ngưỡng hành động IPM. Phun thuốc đặc trị liều tiêu chuẩn.',
    3: 'Nhiễm nặng. Phun thuốc đặc trị liều tăng cường, cách ly khu vực bệnh, ngưng bón phân đạm.',
    4: 'Nguy kịch. Nhổ bỏ và tiêu hủy cây nhiễm nặng, xử lý đất bằng vôi bột.',
}


def severity_level(lesion_area_px: int, leaf_area_px: int) -> int:
    """Cấp 0–4. So sánh bằng số nguyên để không lệch ở đúng ngưỡng 5%, 15%, 35%."""
    if leaf_area_px <= 0:
        raise ValueError('leaf_area_px phải lớn hơn 0')
    if lesion_area_px == 0:
        return 0
    percent_x_leaf = lesion_area_px * 100 # S < n%  <=>  lesion * 100 < n * leaf
    if percent_x_leaf < 5 * leaf_area_px:
        return 1
    if percent_x_leaf < 15 * leaf_area_px:
        return 2
    if percent_x_leaf <= 35 * leaf_area_px:
        return 3
    return 4
