import {
  Alert, Box, Button, Checkbox, FormControlLabel, FormHelperText, Link, Stack, TextField, Typography,
} from '@mui/material';
import { useState } from 'react';
import { Navigate, Link as RouterLink, useNavigate } from 'react-router';

import { errorMessage, fieldErrors } from '../api/client';
import { useAuth } from '../auth/context';
import AuthShell from '../components/AuthShell';

const EMPTY_FORM = { email: '', fullname: '', password: '', confirmPassword: '', acceptTerms: false };
const PASSWORD_MISMATCH = 'Mật khẩu nhập lại không khớp.';

export default function RegisterPage() {
  const { isAuthenticated, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({}); // lỗi theo trường, trả từ backend (đã là tiếng Việt)
  const [error, setError] = useState(''); // lỗi chung (mất kết nối, máy chủ lỗi...)
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  function update(field) {
    return (event) => {
      const value = field === 'acceptTerms' ? event.target.checked : event.target.value;
      setForm((current) => ({ ...current, [field]: value }));
      setErrors((current) => ({ ...current, [field]: undefined }));
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (form.password !== form.confirmPassword) {
      setErrors({ confirmPassword: PASSWORD_MISMATCH });
      return;
    }
    setSubmitting(true);
    try {
      await register({
        email: form.email.trim(),
        fullname: form.fullname.trim(),
        password: form.password,
        acceptTerms: form.acceptTerms,
      });
      navigate('/', { replace: true }); // đăng ký xong vào thẳng trang Tải ảnh
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors({ email: byField.email, fullname: byField.fullname, password: byField.password,
        acceptTerms: byField.accept_terms });
      // Lỗi không gắn với ô nào (hoặc không phải lỗi 400) thì hiện ở khung đỏ phía trên
      const known = ['email', 'fullname', 'password', 'accept_terms'];
      if (Object.keys(byField).every((field) => !known.includes(field))) setError(errorMessage(err));
      setSubmitting(false);
    }
  }

  const canSubmit = form.email && form.fullname && form.password && form.confirmPassword
    && form.acceptTerms && !submitting;

  return (
    <AuthShell title="Đăng ký tài khoản" subtitle="Tạo tài khoản để chẩn đoán và lưu lại lịch sử."
      maxWidth={480}>
      <Stack component="form" spacing={2} onSubmit={handleSubmit} noValidate>
        {error && <Alert severity="error">{error}</Alert>}
        <TextField label="Email" type="email" autoComplete="email" required autoFocus
          value={form.email} onChange={update('email')}
          error={Boolean(errors.email)} helperText={errors.email} />
        <TextField label="Họ và tên" autoComplete="name" required
          value={form.fullname} onChange={update('fullname')}
          error={Boolean(errors.fullname)} helperText={errors.fullname} />
        <TextField label="Mật khẩu" type="password" autoComplete="new-password" required
          value={form.password} onChange={update('password')}
          error={Boolean(errors.password)}
          helperText={errors.password ?? 'Ít nhất 8 ký tự, không quá phổ biến, không giống email hay họ tên.'} />
        <TextField label="Nhập lại mật khẩu" type="password" autoComplete="new-password" required
          value={form.confirmPassword} onChange={update('confirmPassword')}
          error={Boolean(errors.confirmPassword)} helperText={errors.confirmPassword} />
        <Box>
          <FormControlLabel
            control={<Checkbox checked={form.acceptTerms} onChange={update('acceptTerms')} />}
            label={(
              <>
                Tôi đã đọc và đồng ý{' '}
                {/* Mở tab mới để không mất dữ liệu đang nhập */}
                <Link component={RouterLink} to="/terms" target="_blank" rel="noopener">
                  điều khoản sử dụng
                </Link>
              </>
            )}
          />
          {errors.acceptTerms && <FormHelperText error>{errors.acceptTerms}</FormHelperText>}
        </Box>
        <Button type="submit" variant="contained" size="large" disabled={!canSubmit}>
          {submitting ? 'Đang đăng ký…' : 'Đăng ký'}
        </Button>
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
          Đã có tài khoản?{' '}
          <Link component={RouterLink} to="/login" sx={{ fontWeight: 600 }}>Đăng nhập</Link>
        </Typography>
      </Stack>
    </AuthShell>
  );
}
