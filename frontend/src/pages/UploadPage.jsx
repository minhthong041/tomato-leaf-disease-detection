import AddPhotoAlternateOutlinedIcon from '@mui/icons-material/AddPhotoAlternateOutlined';
import BiotechOutlinedIcon from '@mui/icons-material/BiotechOutlined';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CropFreeIcon from '@mui/icons-material/CropFree';
import FilterVintageOutlinedIcon from '@mui/icons-material/FilterVintageOutlined';
import ImageSearchIcon from '@mui/icons-material/ImageSearch';
import TuneIcon from '@mui/icons-material/Tune';
import {
  Alert, Box, Button, Card, CardContent, CircularProgress, Stack, Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';

import { errorMessage } from '../api/client';
import { createDiagnosis } from '../api/diagnoses';
import PageHeader from '../components/PageHeader';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png'];

const PHOTO_TIPS = [
  'Chỉ một chiếc lá cà chua trong ảnh',
  'Đặt lá trên nền đơn sắc: tờ giấy trắng, mặt bàn trơn',
  'Đủ sáng, tránh bóng đổ đậm lên lá',
  'Chụp rõ nét, lá chiếm phần lớn khung hình',
];

// Các giai đoạn hệ thống chạy sau khi bấm Chẩn đoán (theo docs/pipeline.md)
const PIPELINE_STAGES = [
  { icon: <TuneIcon />, title: 'Tiền xử lý', text: 'Chuẩn hóa kích thước, khử nhiễu, cân bằng sáng' },
  { icon: <CropFreeIcon />, title: 'Tách lá', text: 'Loại bỏ nền, giữ lại phiến lá' },
  { icon: <FilterVintageOutlinedIcon />, title: 'Tìm vết bệnh', text: 'Tách đốm bệnh, tính tỷ lệ S và cấp độ' },
  { icon: <BiotechOutlinedIcon />, title: 'Nhận diện bệnh', text: 'Đặc trưng màu, kết cấu → tên bệnh' },
];

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [dragging, setDragging] = useState(false);

  // Giải phóng URL xem trước cũ khi đổi ảnh hoặc rời trang
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  function selectFile(selected) {
    if (!selected) return;
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setError('Chỉ nhận ảnh JPG hoặc PNG.');
      return;
    }
    setError('');
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
  }

  function handleFileChange(event) {
    const selected = event.target.files?.[0];
    event.target.value = ''; // cho phép chọn lại cùng một file
    selectFile(selected);
  }

  // Kéo thả ảnh vào vùng chọn ảnh: kiểm tra giống hệt khi chọn bằng nút
  function handleDragOver(event) {
    event.preventDefault();
    if (!submitting) setDragging(true);
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    if (!submitting) selectFile(event.dataTransfer.files?.[0]);
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

  const fileInput = (
    <input hidden type="file" accept={ACCEPTED_TYPES.join(',')} onChange={handleFileChange} disabled={submitting} />
  );

  return (
    <Stack spacing={{ xs: 3, md: 4 }}>
      <PageHeader
        overline="Chẩn đoán mới"
        title="Chẩn đoán bệnh lá cà chua"
        description={(
          <>
            Tải lên ảnh chụp <strong>một chiếc lá cà chua</strong>, đặt trên <strong>nền đơn sắc</strong>. Hệ thống
            tách lá khỏi nền, tìm vết bệnh, tính tỷ lệ diện tích bệnh, xếp cấp độ và nhận diện tên bệnh.
          </>
        )}
      />

      {error && <Alert severity="error">{error}</Alert>}

      <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: '7fr 5fr' }, alignItems: 'start' }}>
        <Card>
          <CardContent sx={{ p: { xs: 2, sm: 3 }, '&:last-child': { pb: { xs: 2, sm: 3 } } }}>
            <Box
              component="label"
              onDragOver={handleDragOver}
              onDragLeave={(event) => !event.currentTarget.contains(event.relatedTarget) && setDragging(false)}
              onDrop={handleDrop}
              sx={(theme) => ({
                display: 'block', cursor: submitting ? 'default' : 'pointer', borderRadius: '12px', overflow: 'hidden',
                border: `2px dashed ${dragging ? theme.palette.primary.main : theme.palette.divider}`,
                bgcolor: dragging ? alpha(theme.palette.primary.main, 0.06) : '#fafbf8',
                transition: 'border-color 0.15s, background-color 0.15s',
                '&:hover': submitting ? {} : { borderColor: theme.palette.primary.main },
                '&:focus-within': { outline: `2px solid ${theme.palette.primary.main}`, outlineOffset: 2 },
              })}
            >
              {fileInput}
              {preview ? (
                <Box component="img" src={preview} alt="Ảnh lá cà chua đã chọn"
                  sx={{ display: 'block', width: '100%', height: { xs: 280, sm: 380 }, objectFit: 'contain' }} />
              ) : (
                <Stack spacing={1.5} sx={{ height: { xs: 260, sm: 380 }, alignItems: 'center', justifyContent: 'center', px: 3, textAlign: 'center' }}>
                  <Box sx={{
                    width: 72, height: 72, borderRadius: '50%', display: 'grid', placeItems: 'center',
                    bgcolor: 'primary.light', color: 'primary.main',
                  }}>
                    <AddPhotoAlternateOutlinedIcon sx={{ fontSize: 36 }} />
                  </Box>
                  <Typography variant="h6" component="p">Bấm để chọn ảnh lá cà chua</Typography>
                  <Typography color="text.secondary" variant="body2">
                    hoặc kéo thả ảnh vào đây · JPG hoặc PNG, tối đa 10 MB
                  </Typography>
                </Stack>
              )}
            </Box>

            {file && (
              <Typography variant="body2" color="text.secondary" noWrap sx={{ mt: 1.5 }}>
                {file.name} · {formatSize(file.size)}
              </Typography>
            )}

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mt: 2 }}>
              <Button variant="outlined" size="large" component="label" disabled={submitting}
                startIcon={<AddPhotoAlternateOutlinedIcon />}>
                {file ? 'Đổi ảnh khác' : 'Chọn ảnh lá cà chua'}
                {fileInput}
              </Button>
              <Button variant="contained" size="large" disabled={!file || submitting} onClick={handleSubmit}
                startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <ImageSearchIcon />}
                sx={{ flexGrow: 1 }}>
                {submitting ? 'Đang gửi…' : 'Chẩn đoán'}
              </Button>
            </Stack>
          </CardContent>
        </Card>

        <Card sx={{ bgcolor: 'primary.light', borderColor: 'transparent' }}>
          <CardContent sx={{ p: 3, '&:last-child': { pb: 3 } }}>
            <Typography variant="h6" component="h2" sx={{ mb: 2 }}>Mẹo chụp ảnh để kết quả chính xác</Typography>
            <Stack component="ul" spacing={1.5} sx={{ m: 0, p: 0, listStyle: 'none' }}>
              {PHOTO_TIPS.map((tip) => (
                <Stack component="li" key={tip} direction="row" spacing={1.25} sx={{ alignItems: 'flex-start' }}>
                  <CheckCircleIcon color="primary" fontSize="small" sx={{ mt: 0.25 }} />
                  <Typography>{tip}</Typography>
                </Stack>
              ))}
            </Stack>
            <Alert severity="warning" sx={{ mt: 2.5, bgcolor: 'background.paper' }}>
              Ảnh chụp ngoài đồng ruộng (nhiều lá chồng nhau, nền đất, cỏ) thường cho kết quả sai.
            </Alert>
          </CardContent>
        </Card>
      </Box>

      <Box>
        <Typography variant="overline" color="text.secondary">Hệ thống xử lý ảnh của bạn thế nào</Typography>
        <Box sx={{
          mt: 1, display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(4, 1fr)' },
        }}>
          {PIPELINE_STAGES.map((stage, index) => (
            <Card key={stage.title}>
              <CardContent sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                <Box sx={{
                  width: 40, height: 40, borderRadius: '10px', flexShrink: 0, display: 'grid', placeItems: 'center',
                  bgcolor: 'primary.light', color: 'primary.main',
                }}>
                  {stage.icon}
                </Box>
                <Box>
                  <Typography variant="subtitle2">{index + 1}. {stage.title}</Typography>
                  <Typography variant="body2" color="text.secondary">{stage.text}</Typography>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>
    </Stack>
  );
}
