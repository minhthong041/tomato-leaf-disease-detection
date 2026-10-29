import BookmarkIcon from '@mui/icons-material/Bookmark';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import { Alert, Button, Snackbar } from '@mui/material';
import { useState } from 'react';

import { errorMessage } from '../api/client';
import { setBookmark } from '../api/diagnoses';

// Nút lưu / bỏ lưu một kết quả chẩn đoán. onChange nhận bản ghi mới backend trả về.
export default function BookmarkButton({ diagnosis, onChange }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const saved = diagnosis.is_bookmarked;

  async function handleClick() {
    setSaving(true);
    try {
      onChange(await setBookmark(diagnosis.id, !saved));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Button variant={saved ? 'contained' : 'outlined'} disabled={saving} onClick={handleClick}
        startIcon={saved ? <BookmarkIcon /> : <BookmarkBorderIcon />} aria-pressed={saved}>
        {saved ? 'Đã lưu' : 'Lưu kết quả'}
      </Button>
      <Snackbar open={Boolean(error)} autoHideDuration={5000} onClose={() => setError('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="error" variant="filled" onClose={() => setError('')}>{error}</Alert>
      </Snackbar>
    </>
  );
}
