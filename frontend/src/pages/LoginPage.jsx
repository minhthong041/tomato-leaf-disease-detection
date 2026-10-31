import { Alert, Button, Link, Stack, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { Navigate, Link as RouterLink, useLocation, useNavigate } from 'react-router';

import { errorMessage } from '../api/client';
import { useAuth } from '../auth/context';
import AuthShell from '../components/AuthShell';

export default function LoginPage() {
  const { isAuthenticated, notice, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const redirectTo = location.state?.from?.pathname ?? '/';
  if (isAuthenticated) return <Navigate to={redirectTo} replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell title="Đăng nhập" subtitle="Chào mừng bạn quay lại. Đăng nhập để chẩn đoán và xem lịch sử.">
      <Stack component="form" spacing={2} onSubmit={handleSubmit} noValidate>
        {notice && !error && <Alert severity="success">{notice}</Alert>}
        {error && <Alert severity="error">{error}</Alert>}
        <TextField label="Email" type="email" autoComplete="email" required autoFocus
          value={email} onChange={(e) => setEmail(e.target.value)} />
        <TextField label="Mật khẩu" type="password" autoComplete="current-password" required
          value={password} onChange={(e) => setPassword(e.target.value)} />
        <Button type="submit" variant="contained" size="large"
          disabled={submitting || !email || !password}>
          {submitting ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </Button>
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
          Chưa có tài khoản?{' '}
          <Link component={RouterLink} to="/register" sx={{ fontWeight: 600 }}>Đăng ký</Link>
        </Typography>
      </Stack>
    </AuthShell>
  );
}
