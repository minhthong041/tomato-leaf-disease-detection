import { api } from './client';

// API chẩn đoán ở backend/api/views.py (DiagnosisViewSet). Đường dẫn và dữ liệu trả về:
//
// POST /api/diagnoses/        (multipart, trường "image")  -> Diagnosis, status "done" hoặc "failed"
//                             (chạy pipeline đồng bộ, trả về khi xử lý xong)
// GET  /api/diagnoses/        -> { count, next, previous, results: [Diagnosis] } (20 mục/trang)
// GET  /api/diagnoses/:id/    -> Diagnosis
// PATCH /api/diagnoses/:id/   { is_bookmarked } -> Diagnosis
//
// Diagnosis = {
//   id, status: "pending" | "processing" | "done" | "failed", error_message,
//   original_image, processed_image,            // URL đầy đủ
//   disease: { code, name, is_healthy } | null,
//   disease_confidence: "0.9100" | null,         // DRF trả decimal dạng chuỗi
//   severity_level: 0..4 | null, recommendation, // khuyến nghị IPM theo cấp
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

export function listDiagnoses(page = 1) {
  return api.get(`/diagnoses/?page=${page}`);
}

export function getDiagnosis(id) {
  return api.get(`/diagnoses/${id}/`);
}

export function setBookmark(id, isBookmarked) {
  return api.patch(`/diagnoses/${id}/`, { is_bookmarked: isBookmarked });
}
