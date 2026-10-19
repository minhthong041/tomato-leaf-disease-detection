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
