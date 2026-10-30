import { Navigate, Outlet, useLocation } from 'react-router';

import { useAuth } from './context';

// Bọc các trang cần đăng nhập; chưa đăng nhập thì chuyển về /login rồi quay lại trang cũ
export default function RequireAuth() {
  const { isAuthenticated, notice } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    // Có notice (vd. vừa xóa tài khoản) thì đăng nhập lại về trang chủ, không quay lại trang cũ
    return <Navigate to="/login" replace state={notice ? undefined : { from: location }} />;
  }
  return <Outlet />;
}
