import {
  Alert, Box, Button, Card, CardContent, Link, Stack, TextField, Typography,
} from '@mui/material';
import { useState } from 'react';
import { Navigate, Link as RouterLink, useLocation, useNavigate } from 'react-router';

import { errorMessage } from '../api/client';
import { useAuth } from '../auth/context';

export default function LoginPage() {
  const { isAuthenticated, login } = useAuth();
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
    <Box sx={{ maxWidth: 420, mx: 'auto' }}>
      <Card>
        <CardContent>
          <Typography variant="h5" component="h1" gutterBottom>
            Đăng nhập
          </Typography>
          <Stack component="form" spacing={2} onSubmit={handleSubmit} noValidate>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField label="Email" type="email" autoComplete="email" required autoFocus
              value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextField label="Mật khẩu" type="password" autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} />
            <Button type="submit" variant="contained" size="large"
              disabled={submitting || !email || !password}>
              {submitting ? 'Đang đăng nhập…' : 'Đăng nhập'}
            </Button>
            <Typography variant="body2" sx={{ textAlign: 'center' }}>
              Chưa có tài khoản?{' '}
              <Link component={RouterLink} to="/register">Đăng ký</Link>
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
