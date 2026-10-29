import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Snackbar, Stack,
  TextField,
} from '@mui/material';
import { useState } from 'react';

import { errorMessage, fieldErrors } from '../api/client';
import { createFeedback } from '../api/reports';

const EMPTY_FORM = { title: '', description: '' };
const TITLE_MAX_LENGTH = 255; // trùng feedbacks.title
const DESCRIPTION_MAX_LENGTH = 5000; // trùng REPORT_DESCRIPTION_MAX_LENGTH ở backend

// Nút "Báo kết quả sai" trên trang Kết quả, mở hộp thoại gửi phản hồi cho lần chẩn đoán historyId
export default function FeedbackDialog({ historyId }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  function update(field) {
    return (event) => {
      setForm((current) => ({ ...current, [field]: event.target.value }));
      setErrors((current) => ({ ...current, [field]: undefined }));
    };
  }

  function handleClose() {
    if (submitting) return;
    setOpen(false);
    setErrors({});
    setError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await createFeedback(historyId, { title: form.title.trim(), description: form.description.trim() });
      setOpen(false);
      setForm(EMPTY_FORM);
      setSent(true);
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors({ title: byField.title, description: byField.description });
      if (!byField.title && !byField.description) setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit = form.title.trim() && form.description.trim() && !submitting;

  return (
    <>
      <Button variant="outlined" color="warning" startIcon={<ReportProblemIcon />} onClick={() => setOpen(true)}>
        Báo kết quả sai
      </Button>

      <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
        <form onSubmit={handleSubmit} noValidate>
          <DialogTitle>Báo kết quả sai</DialogTitle>
          <DialogContent>
            <Stack spacing={2}>
              <DialogContentText>
                Cho chúng tôi biết kết quả chẩn đoán này sai ở đâu (tên bệnh, cấp độ, vùng đốm bệnh…).
                Quản trị viên sẽ xem lại.
              </DialogContentText>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField label="Tiêu đề" required autoFocus
                placeholder="Ví dụ: Lá khỏe nhưng bị kết luận bệnh nặng"
                value={form.title} onChange={update('title')}
                slotProps={{ htmlInput: { maxLength: TITLE_MAX_LENGTH } }}
                error={Boolean(errors.title)} helperText={errors.title} />
              <TextField label="Mô tả" required multiline minRows={4}
                value={form.description} onChange={update('description')}
                slotProps={{ htmlInput: { maxLength: DESCRIPTION_MAX_LENGTH } }}
                error={Boolean(errors.description)} helperText={errors.description} />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose} disabled={submitting}>Hủy</Button>
            <Button type="submit" variant="contained" disabled={!canSubmit}>
              {submitting ? 'Đang gửi…' : 'Gửi phản hồi'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Snackbar open={sent} autoHideDuration={5000} onClose={() => setSent(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="success" variant="filled" onClose={() => setSent(false)}>
          Đã gửi phản hồi. Cảm ơn bạn!
        </Alert>
      </Snackbar>
    </>
  );
}
