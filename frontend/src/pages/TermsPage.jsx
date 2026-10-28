import { Box, Card, CardContent, Link, Stack, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router';

import { useAuth } from '../auth/context';
import { TERMS_VERSION } from '../constants/terms';

// Mỗi mục: tiêu đề và các đoạn nội dung. Sửa nội dung thì tăng TERMS_VERSION (frontend và backend).
const SECTIONS = [
  {
    title: '1. Dịch vụ',
    paragraphs: [
      'Hệ thống nhận ảnh một chiếc lá cà chua, tách lá khỏi nền, tìm vết bệnh, tính tỷ lệ diện tích lá bị '
      + 'bệnh, xếp cấp độ 0–4 kèm khuyến nghị xử lý theo IPM và nhận diện tên bệnh. Đây là sản phẩm của đồ án '
      + 'môn Xử lý ảnh số, phục vụ học tập và thử nghiệm.',
    ],
  },
  {
    title: '2. Kết quả chỉ để tham khảo',
    paragraphs: [
      'Kết quả chẩn đoán (tên bệnh, độ tin cậy, tỷ lệ diện tích bệnh, cấp độ và khuyến nghị) được tạo tự '
      + 'động bằng thuật toán xử lý ảnh và học máy, có thể sai, nhất là với ảnh chụp ngoài đồng ruộng.',
      'Kết quả chỉ để tham khảo và không thay thế ý kiến của chuyên gia nông nghiệp hoặc cán bộ bảo vệ thực '
      + 'vật. Trước khi dùng thuốc bảo vệ thực vật, nhổ bỏ cây hay xử lý đất, hãy hỏi ý kiến chuyên gia.',
    ],
  },
  {
    title: '3. Ảnh và dữ liệu của bạn',
    paragraphs: [
      'Ảnh bạn tải lên được xóa thông tin EXIF (vị trí GPS, thiết bị chụp) trước khi lưu, và được đặt tên '
      + 'ngẫu nhiên, không chứa tên hay mã người dùng.',
      'Khi bạn xóa tài khoản, email, tên đăng nhập và họ tên bị xóa. Ảnh đã tải lên và kết quả chẩn đoán '
      + 'vẫn được giữ lại ở dạng ẩn danh (không còn gắn với thông tin cá nhân của bạn) để thống kê và cải '
      + 'thiện hệ thống.',
    ],
  },
  {
    title: '4. Tài khoản',
    paragraphs: [
      'Bạn chịu trách nhiệm giữ bí mật mật khẩu. Không tải lên ảnh không liên quan, ảnh có nội dung vi phạm '
      + 'pháp luật hoặc ảnh chứa thông tin cá nhân của người khác.',
    ],
  },
  {
    title: '5. Thay đổi điều khoản',
    paragraphs: [
      'Khi điều khoản thay đổi, số phiên bản ở đầu trang sẽ tăng. Hệ thống lưu phiên bản bạn đã đồng ý '
      + 'cùng thời điểm đồng ý.',
    ],
  },
];

export default function TermsPage() {
  const { isAuthenticated } = useAuth();

  return (
    <Card>
      <CardContent>
        <Stack spacing={3}>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              Điều khoản sử dụng
            </Typography>
            <Typography color="text.secondary">Phiên bản {TERMS_VERSION}</Typography>
          </Box>
          {SECTIONS.map((section) => (
            <Box key={section.title}>
              <Typography variant="h6" component="h2" gutterBottom>{section.title}</Typography>
              {section.paragraphs.map((text) => (
                <Typography key={text} sx={{ mb: 1.5 }}>{text}</Typography>
              ))}
            </Box>
          ))}
          <Typography variant="body2">
            {isAuthenticated
              ? <Link component={RouterLink} to="/">Về trang chủ</Link>
              : <Link component={RouterLink} to="/register">Quay lại trang đăng ký</Link>}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}
