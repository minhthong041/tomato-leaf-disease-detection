import BiotechOutlinedIcon from '@mui/icons-material/BiotechOutlined';
import CropFreeIcon from '@mui/icons-material/CropFree';
import SpeedIcon from '@mui/icons-material/Speed';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';

const FEATURES = [
  { icon: <CropFreeIcon />, title: 'Tách lá, khoanh vết bệnh', text: 'Loại bỏ nền và khoanh vùng từng đốm bệnh trên lá.' },
  { icon: <SpeedIcon />, title: 'Chấm cấp độ 0–4', text: 'Đo tỷ lệ diện tích bệnh S để xếp cấp, kèm khuyến nghị IPM.' },
  { icon: <BiotechOutlinedIcon />, title: 'Nhận diện tên bệnh', text: 'Phân biệt 9 loại bệnh, sâu hại thường gặp và lá khỏe.' },
];

// Khung trang Đăng nhập / Đăng ký: desktop chia hai cột (giới thiệu | form), điện thoại chỉ có form
export default function AuthShell({ title, subtitle, maxWidth = 440, children }) {
  return (
    <Box sx={{
      display: 'grid', gap: { xs: 3, md: 6 }, alignItems: 'center',
      gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, maxWidth: 1040, mx: 'auto',
    }}>
      <Box sx={{
        display: { xs: 'none', md: 'block' }, p: 5, borderRadius: '20px', color: 'common.white',
        background: 'linear-gradient(150deg, #1f6f43 0%, #15542f 60%, #0f3d22 100%)',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Hai vòng tròn trang trí: lá xanh và quả cà chua */}
        <Box aria-hidden sx={{
          position: 'absolute', width: 220, height: 220, borderRadius: '50%', right: -70, top: -70,
          bgcolor: 'rgba(255, 255, 255, 0.08)',
        }} />
        <Box aria-hidden sx={{
          position: 'absolute', width: 120, height: 120, borderRadius: '50%', right: -56, bottom: -56,
          bgcolor: 'secondary.main', opacity: 0.85,
        }} />
        <Typography variant="overline" sx={{ opacity: 0.8 }}>Đồ án môn Xử lý ảnh</Typography>
        <Typography variant="h4" component="p" sx={{ mt: 1, mb: 4, maxWidth: 380 }}>
          Chụp một chiếc lá cà chua, biết ngay bệnh gì và nặng tới đâu.
        </Typography>
        <Stack spacing={3} sx={{ position: 'relative' }}>
          {FEATURES.map((feature) => (
            <Stack key={feature.title} direction="row" spacing={2} sx={{ alignItems: 'flex-start' }}>
              <Box sx={{
                width: 40, height: 40, borderRadius: '10px', flexShrink: 0, display: 'grid', placeItems: 'center',
                bgcolor: 'rgba(255, 255, 255, 0.14)',
              }}>
                {feature.icon}
              </Box>
              <Box>
                <Typography sx={{ fontWeight: 600 }}>{feature.title}</Typography>
                <Typography variant="body2" sx={{ opacity: 0.8 }}>{feature.text}</Typography>
              </Box>
            </Stack>
          ))}
        </Stack>
      </Box>

      <Card sx={{ width: '100%', maxWidth, mx: 'auto' }}>
        <CardContent sx={{ p: { xs: 3, sm: 4 }, '&:last-child': { pb: { xs: 3, sm: 4 } } }}>
          <Typography variant="h5" component="h1">{title}</Typography>
          {subtitle && <Typography color="text.secondary" sx={{ mt: 0.5, mb: 3 }}>{subtitle}</Typography>}
          {children}
        </CardContent>
      </Card>
    </Box>
  );
}
