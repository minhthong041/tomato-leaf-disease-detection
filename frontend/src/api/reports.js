import { api } from './client';

// POST /api/feedbacks/ { history, title, description } -> báo một kết quả chẩn đoán bị sai.
// Lần chẩn đoán không phải của mình (hoặc không tồn tại) -> 404.
export function createFeedback(historyId, { title, description }) {
  return api.post('/feedbacks/', { history: historyId, title, description });
}

// POST /api/error-reports/ { title, description } -> báo lỗi ứng dụng. Người gửi lấy từ tài khoản đăng nhập.
export function createErrorReport({ title, description }) {
  return api.post('/error-reports/', { title, description });
}
