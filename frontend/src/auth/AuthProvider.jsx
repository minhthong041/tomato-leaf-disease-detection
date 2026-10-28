import { useCallback, useEffect, useMemo, useState } from 'react';

import { login as apiLogin, logout as apiLogout, register as apiRegister } from '../api/auth';
import { setUnauthorizedHandler, tokens } from '../api/client';
import { AuthContext } from './context';

export default function AuthProvider({ children }) {
  // Backend chưa có API lấy thông tin người dùng: còn refresh token thì coi là đã đăng nhập
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(tokens.refresh));

  useEffect(() => {
    setUnauthorizedHandler(() => setIsAuthenticated(false));
  }, []);

  const login = useCallback(async (email, password) => {
    await apiLogin(email, password);
    setIsAuthenticated(true);
  }, []);

  const register = useCallback(async (form) => {
    await apiRegister(form);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setIsAuthenticated(false);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, login, register, logout }),
    [isAuthenticated, login, register, logout],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}
