import { ApiError, request, tokens } from './client';

export async function login(email, password) {
  try {
    const data = await request('/auth/login/', {
      method: 'POST',
      body: { email, password },
      auth: false,
    });
    tokens.set(data.access, data.refresh);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      throw new ApiError(401, { detail: 'Email hoặc mật khẩu không đúng.' });
    }
    throw error;
  }
}

// Đăng ký xong backend trả luôn cặp token -> coi như đã đăng nhập
export async function register({ email, fullname, password, acceptTerms }) {
  const data = await request('/auth/register/', {
    method: 'POST',
    body: { email, fullname, password, accept_terms: acceptTerms },
    auth: false,
  });
  tokens.set(data.access, data.refresh);
}

export async function logout() {
  const refresh = tokens.refresh;
  tokens.clear();
  if (!refresh) return;
  // Đưa refresh token vào blacklist; lỗi mạng ở đây không cản việc đăng xuất
  await request('/auth/logout/', { method: 'POST', body: { refresh }, auth: false }).catch(() => {});
}

// Xóa tài khoản của chính mình (backend ẩn danh hóa, thu hồi mọi refresh token).
// Sai mật khẩu: ApiError 400 với lỗi ở trường password.
export async function deleteAccount(password) {
  await request('/auth/delete-account/', { method: 'POST', body: { password } });
  tokens.clear();
}
