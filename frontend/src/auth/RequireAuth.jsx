import { Navigate, Outlet, useLocation } from 'react-router';

import { useAuth } from './context';

// Bọc các trang cần đăng nhập; chưa đăng nhập thì chuyển về /login rồi quay lại trang cũ
export default function RequireAuth() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
