import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import {
  Alert, Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  Stack, TextField, Typography,
} from '@mui/material';
import { useState } from 'react';

import { errorMessage, fieldErrors } from '../api/client';
import { useAuth } from '../auth/context';

// Trang "Tài khoản": hiện có mục xóa tài khoản (ẩn danh hóa, không xóa cứng)
export default function AccountPage() {
  const { deleteAccount } = useAuth();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function handleClose() {
    if (submitting) return;
    setOpen(false);
    setPassword('');
    setPasswordError('');
    setError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setPasswordError('');
    setSubmitting(true);
    try {
      // Xong thì RequireAuth tự chuyển về /login (trang đó báo đã xóa tài khoản)
      await deleteAccount(password);
    } catch (err) {
      const byField = fieldErrors(err);
      if (byField.password) setPasswordError(byField.password);
      else setError(errorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto' }}>
      <Typography variant="h5" component="h1" gutterBottom>
        Tài khoản
      </Typography>
      <Card variant="outlined" sx={{ borderColor: 'error.main' }}>
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h6" component="h2" color="error">
              Xóa tài khoản
            </Typography>
            <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
              <li>Email và họ tên của bạn bị xóa, bạn bị đăng xuất trên mọi thiết bị và không đăng nhập lại được.</li>
              <li>Lịch sử chẩn đoán vẫn được giữ nhưng không còn gắn với thông tin cá nhân của bạn.</li>
              <li>Bạn có thể dùng lại email này để đăng ký tài khoản mới (tài khoản mới không thấy lịch sử cũ).</li>
            </Box>
            <Alert severity="warning">Không thể hoàn tác sau khi xóa.</Alert>
            <Button variant="contained" color="error" startIcon={<DeleteForeverIcon />}
              onClick={() => setOpen(true)} sx={{ alignSelf: 'flex-start' }}>
              Xóa tài khoản
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Dialog open={open} onClose={handleClose} fullWidth maxWidth="xs">
        <form onSubmit={handleSubmit} noValidate>
          <DialogTitle>Xác nhận xóa tài khoản</DialogTitle>
          <DialogContent>
            <Stack spacing={2}>
              <DialogContentText>Nhập lại mật khẩu để xác nhận. Việc này không thể hoàn tác.</DialogContentText>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField label="Mật khẩu" type="password" autoComplete="current-password" required autoFocus
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setPasswordError('');
                }}
                error={Boolean(passwordError)} helperText={passwordError} />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose} disabled={submitting}>Hủy</Button>
            <Button type="submit" variant="contained" color="error" disabled={!password || submitting}>
              {submitting ? 'Đang xóa…' : 'Xóa vĩnh viễn'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
}
