// Thang Cấp 0–4 (trùng DiagnosisHistory.SeverityLevel ở backend), S = tỷ lệ diện tích bệnh
export const SEVERITY_LEVELS = [
  { level: 0, label: 'Cấp 0 - Khỏe mạnh', range: 'S = 0%', color: '#2e7d32' },
  { level: 1, label: 'Cấp 1 - Nhiễm nhẹ', range: '0% < S < 5%', color: '#9e9d24' },
  { level: 2, label: 'Cấp 2 - Trung bình', range: '5% ≤ S < 15%', color: '#f9a825' },
  { level: 3, label: 'Cấp 3 - Nặng', range: '15% ≤ S ≤ 35%', color: '#ef6c00' },
  { level: 4, label: 'Cấp 4 - Nguy kịch', range: 'S > 35%', color: '#c62828' },
];

// Tên bước trùng DiagnosisStep.Step ở backend
export const STEP_LABELS = {
  resized: 'Chuẩn hóa kích thước',
  denoised: 'Khử nhiễu',
  clahe: 'Cân bằng sáng CLAHE',
  saturation: 'Kênh S (HSV)',
  leaf_mask: 'Mặt nạ lá',
  roi: 'Vùng lá (ROI)',
  healthy_mask: 'Mặt nạ mô lá khỏe',
  lesion_mask_raw: 'Mặt nạ vết bệnh (trước hình thái học)',
  lesion_mask: 'Mặt nạ vết bệnh (sau opening/closing)',
};

export const STATUS_LABELS = {
  pending: 'Chờ xử lý',
  processing: 'Đang xử lý',
  done: 'Hoàn tất',
  failed: 'Lỗi',
};

// DRF trả decimal dạng chuỗi ("0.0850") -> "8.50%"
export function formatPercent(ratio, digits = 2) {
  return ratio == null ? '—' : `${(Number(ratio) * 100).toFixed(digits)}%`;
}

// Dưới ngưỡng này trang Kết quả cảnh báo "độ tin cậy thấp".
// Tạm đặt 0,6; cập nhật theo đề xuất ngưỡng của việc 3E (đánh giá mô hình).
export const LOW_CONFIDENCE_THRESHOLD = 0.6;

// Bệnh do virus: lá xoăn, vàng hoặc khảm màu chứ không có đốm riêng, nên Cấp 0 (không tách được vết bệnh)
// là kết quả bình thường. Bộ mask chuẩn 1D: 6/6 ảnh của hai lớp này có mask vết bệnh rỗng.
// Trùng diseases.code ở backend.
export const NO_LESION_DISEASE_CODES = [
  'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
  'Tomato___Tomato_mosaic_virus',
];

// Các lý do nên nghi ngờ một kết quả đã xong (status "done"). Trả mảng câu cảnh báo, rỗng nếu không có gì.
export function resultWarnings(diagnosis) {
  const warnings = [];
  const { disease, severity_level: level } = diagnosis;
  const confidence = diagnosis.disease_confidence == null ? null : Number(diagnosis.disease_confidence);

  if (confidence != null && confidence < LOW_CONFIDENCE_THRESHOLD) {
    warnings.push(
      `Độ tin cậy chỉ ${formatPercent(confidence, 1)}, thấp hơn ngưỡng ${formatPercent(LOW_CONFIDENCE_THRESHOLD, 0)}: `
      + 'mô hình chưa chắc chắn về tên bệnh.',
    );
  }
  // Tên bệnh (bước phân loại) và cấp độ (bước phân vùng) tính riêng nên có thể mâu thuẫn nhau
  if (disease && level != null) {
    if (disease.is_healthy && level >= 1) {
      warnings.push(`Mô hình kết luận lá khỏe nhưng vẫn phát hiện vết bệnh (Cấp ${level}).`);
    } else if (!disease.is_healthy && level === 0 && !NO_LESION_DISEASE_CODES.includes(disease.code)) {
      warnings.push(`Mô hình kết luận ${disease.name} nhưng không phát hiện vết bệnh nào (Cấp 0).`);
    }
  }
  return warnings;
}
