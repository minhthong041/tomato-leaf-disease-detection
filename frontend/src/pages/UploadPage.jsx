import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { Alert, Box, Button, Card, CardContent, CardMedia, Stack, Typography } from '@mui/material';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';

import { errorMessage } from '../api/client';
import { createDiagnosis } from '../api/diagnoses';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png'];

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Giải phóng URL xem trước cũ khi đổi ảnh hoặc rời trang
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  function handleFileChange(event) {
    const selected = event.target.files?.[0];
    event.target.value = ''; // cho phép chọn lại cùng một file
    if (!selected) return;
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setError('Chỉ nhận ảnh JPG hoặc PNG.');
      return;
    }
    setError('');
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
  }

  async function handleSubmit() {
    setError('');
    setSubmitting(true);
    try {
      const diagnosis = await createDiagnosis(file);
      navigate(`/results/${diagnosis.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Chẩn đoán bệnh lá cà chua
        </Typography>
        <Typography color="text.secondary">
          Tải lên ảnh chụp <strong>một chiếc lá cà chua</strong>, đặt trên nền đơn sắc. Hệ thống tách lá khỏi nền,
          tìm vết bệnh, tính tỷ lệ diện tích bệnh, xếp cấp độ và nhận diện tên bệnh.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      <Card>
        {preview ? (
          <CardMedia component="img" image={preview} alt="Ảnh lá cà chua đã chọn"
            sx={{ maxHeight: 360, objectFit: 'contain', bgcolor: 'grey.100' }} />
        ) : (
          <Box sx={{ height: 240, display: 'grid', placeItems: 'center', bgcolor: 'grey.100' }}>
            <Typography color="text.secondary">Chưa chọn ảnh</Typography>
          </Box>
        )}
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <Button variant="outlined" component="label" startIcon={<CloudUploadIcon />}>
              Chọn ảnh lá cà chua
              <input hidden type="file" accept={ACCEPTED_TYPES.join(',')} onChange={handleFileChange} />
            </Button>
            <Button variant="contained" disabled={!file || submitting} onClick={handleSubmit}>
              {submitting ? 'Đang gửi…' : 'Chẩn đoán'}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
