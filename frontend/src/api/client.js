// Gọi backend Django REST. Địa chỉ lấy từ VITE_API_URL (frontend/.env), mặc định chạy local.
const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api').replace(/\/$/, '');

const ACCESS_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

function readStorage(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key, value) {
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  } catch {
    // Trình duyệt chặn localStorage: chỉ mất trạng thái đăng nhập khi tải lại trang
  }
}

export const tokens = {
  get access() {
    return readStorage(ACCESS_KEY);
  },
  get refresh() {
    return readStorage(REFRESH_KEY);
  },
  set(access, refresh) {
    writeStorage(ACCESS_KEY, access);
    if (refresh) writeStorage(REFRESH_KEY, refresh);
  },
  clear() {
    writeStorage(ACCESS_KEY, null);
    writeStorage(REFRESH_KEY, null);
  },
};

export class ApiError extends Error {
  constructor(status, data) {
    super(data?.detail ?? `Lỗi ${status}`);
    this.status = status;
    this.data = data;
  }
}

let onUnauthorized = () => {};

// AuthProvider đăng ký hàm này để chuyển về trạng thái đã đăng xuất khi phiên hết hạn
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

let refreshing = null;

// Refresh token bị xoay vòng (dùng một lần): gộp các lần gọi đồng thời thành một request
function refreshTokens() {
  refreshing ??= (async () => {
    const res = await fetch(`${API_URL}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: tokens.refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    tokens.set(data.access, data.refresh);
    return true;
  })()
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function request(path, { method = 'GET', body, auth = true, retry = true } = {}) {
  const headers = {};
  let payload;
  if (body instanceof FormData) {
    payload = body; // trình duyệt tự đặt Content-Type multipart
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;

  const res = await fetch(`${API_URL}${path}`, { method, headers, body: payload });

  if (res.status === 401 && auth && retry && tokens.refresh && (await refreshTokens())) {
    return request(path, { method, body, auth, retry: false });
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && auth) {
      tokens.clear();
      onUnauthorized();
    }
    throw new ApiError(res.status, data);
  }
  return data;
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
};

// Thông báo lỗi tiếng Việt để hiển thị cho người dùng
export function errorMessage(error) {
  if (!(error instanceof ApiError)) {
    return 'Không kết nối được máy chủ. Kiểm tra backend đã chạy chưa.';
  }
  if (error.status === 404) return 'Không tìm thấy dữ liệu, hoặc API này chưa được làm.';
  if (error.status >= 500) return 'Máy chủ gặp lỗi. Vui lòng thử lại sau.';
  return error.message;
}
