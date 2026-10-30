import { api } from './client';

// API chẩn đoán ở backend/api/views.py (DiagnosisViewSet). Đường dẫn và dữ liệu trả về:
//
// POST /api/diagnoses/        (multipart, trường "image")  -> Diagnosis, status "done" hoặc "failed"
//                             (chạy pipeline đồng bộ, trả về khi xử lý xong)
// GET  /api/diagnoses/        -> { count, next, previous, results: [Diagnosis] } (20 mục/trang)
//                             ?is_bookmarked=true chỉ lấy kết quả đã lưu
// GET  /api/diagnoses/:id/    -> Diagnosis
// PATCH /api/diagnoses/:id/   { is_bookmarked } -> Diagnosis
//
// Diagnosis = {
//   id, status: "pending" | "processing" | "done" | "failed", error_message,
//   original_image, processed_image,            // URL đầy đủ
//   disease: { code, name, is_healthy } | null,
//   disease_confidence: "0.9100" | null,         // DRF trả decimal dạng chuỗi
//   severity_level: 0..4 | null, recommendation, // khuyến nghị IPM theo cấp
//   disease_recommendation: {                    // khuyến nghị theo bệnh (backend/api/recommendations.py)
//     cause: string | null, advice, sources: [{ title, url }],
//     replaces_severity_advice: bool,            // true: không hiện khuyến nghị theo cấp (virus, nhện, lá khỏe)
//     pesticide_note: string | null,
//   } | null,
//   infected_ratio: "0.0850" | null, leaf_area_px, lesion_area_px, lesion_count,
//   lesions: [{ area, perimeter, circularity, center, bbox }],
//   steps: [{ step, image }],                    // theo đúng thứ tự pipeline
//   is_bookmarked, created_at,
// }

export function createDiagnosis(file) {
  const form = new FormData();
  form.append('image', file);
  return api.post('/diagnoses/', form);
}

// bookmarkedOnly = true: chỉ lấy các kết quả đã lưu
export function listDiagnoses(page = 1, { bookmarkedOnly = false } = {}) {
  const params = new URLSearchParams({ page: String(page) });
  if (bookmarkedOnly) params.set('is_bookmarked', 'true');
  return api.get(`/diagnoses/?${params}`);
}

export function getDiagnosis(id) {
  return api.get(`/diagnoses/${id}/`);
}

export function setBookmark(id, isBookmarked) {
  return api.patch(`/diagnoses/${id}/`, { is_bookmarked: isBookmarked });
}
