import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  deleteAccount as apiDeleteAccount, login as apiLogin, logout as apiLogout, register as apiRegister,
} from '../api/auth';
import { setUnauthorizedHandler, tokens } from '../api/client';
import { AuthContext } from './context';

export default function AuthProvider({ children }) {
  // Backend chưa có API lấy thông tin người dùng: còn refresh token thì coi là đã đăng nhập
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(tokens.refresh));
  // Thông báo cho trang Đăng nhập sau khi bị đăng xuất vì lý do đặc biệt (vd. vừa xóa tài khoản)
  const [notice, setNotice] = useState('');

  useEffect(() => {
    setUnauthorizedHandler(() => setIsAuthenticated(false));
  }, []);

  const login = useCallback(async (email, password) => {
    await apiLogin(email, password);
    setNotice('');
    setIsAuthenticated(true);
  }, []);

  const register = useCallback(async (form) => {
    await apiRegister(form);
    setNotice('');
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setIsAuthenticated(false);
  }, []);

  const deleteAccount = useCallback(async (password) => {
    await apiDeleteAccount(password);
    // RequireAuth tự chuyển về /login khi isAuthenticated thành false; trang đó hiện notice
    setNotice('Đã xóa tài khoản. Bạn đã được đăng xuất.');
    setIsAuthenticated(false);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, notice, login, register, logout, deleteAccount }),
    [isAuthenticated, notice, login, register, logout, deleteAccount],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}
