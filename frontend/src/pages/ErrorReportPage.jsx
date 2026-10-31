import { Alert, Button, Card, CardContent, Stack, TextField } from '@mui/material';
import { useState } from 'react';

import { errorMessage, fieldErrors } from '../api/client';
import { createErrorReport } from '../api/reports';
import PageHeader from '../components/PageHeader';

const EMPTY_FORM = { title: '', description: '' };
const TITLE_MAX_LENGTH = 255; // trùng error_reports.title
const DESCRIPTION_MAX_LENGTH = 5000; // trùng REPORT_DESCRIPTION_MAX_LENGTH ở backend

// Trang "Báo lỗi": người dùng gửi lỗi của ứng dụng cho quản trị viên
export default function ErrorReportPage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  function update(field) {
    return (event) => {
      setForm((current) => ({ ...current, [field]: event.target.value }));
      setErrors((current) => ({ ...current, [field]: undefined }));
      setSent(false);
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSent(false);
    setSubmitting(true);
    try {
      await createErrorReport({ title: form.title.trim(), description: form.description.trim() });
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
    <Stack spacing={3} sx={{ maxWidth: 720, mx: 'auto' }}>
      <PageHeader
        overline="Hỗ trợ"
        title="Báo lỗi"
        description={(
          <>
            Gặp lỗi khi dùng ứng dụng? Mô tả lại để quản trị viên xử lý. Nếu một kết quả chẩn đoán bị sai,
            hãy dùng nút &quot;Báo kết quả sai&quot; trên trang kết quả đó.
          </>
        )}
      />
      <Card>
        <CardContent sx={{ p: { xs: 2.5, sm: 3 }, '&:last-child': { pb: { xs: 2.5, sm: 3 } } }}>
          <Stack component="form" spacing={2} onSubmit={handleSubmit} noValidate>
            {sent && <Alert severity="success">Đã gửi báo lỗi. Cảm ơn bạn!</Alert>}
            {error && <Alert severity="error">{error}</Alert>}
            <TextField label="Tiêu đề" required
              placeholder="Ví dụ: Bấm Chẩn đoán thì trang đứng yên"
              value={form.title} onChange={update('title')}
              slotProps={{ htmlInput: { maxLength: TITLE_MAX_LENGTH } }}
              error={Boolean(errors.title)} helperText={errors.title} />
            <TextField label="Mô tả" required multiline minRows={5}
              placeholder="Bạn đang làm gì, lỗi hiện ra thế nào, xảy ra lúc nào…"
              value={form.description} onChange={update('description')}
              slotProps={{ htmlInput: { maxLength: DESCRIPTION_MAX_LENGTH } }}
              error={Boolean(errors.description)} helperText={errors.description} />
            <Button type="submit" variant="contained" size="large" disabled={!canSubmit}
              sx={{ alignSelf: 'flex-start' }}>
              {submitting ? 'Đang gửi…' : 'Gửi báo lỗi'}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
