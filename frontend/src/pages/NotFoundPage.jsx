import SearchOffIcon from '@mui/icons-material/SearchOff';
import { Avatar, Button, Stack, Typography } from '@mui/material';
import { Link } from 'react-router';

export default function NotFoundPage() {
  return (
    <Stack spacing={2} sx={{ py: 8, alignItems: 'center', textAlign: 'center' }}>
      <Avatar sx={{ width: 72, height: 72, bgcolor: 'primary.light', color: 'primary.main' }}>
        <SearchOffIcon fontSize="large" />
      </Avatar>
      <Typography variant="h4" component="h1">Không tìm thấy trang</Typography>
      <Typography color="text.secondary">Đường dẫn không tồn tại hoặc đã bị thay đổi.</Typography>
      <Button component={Link} to="/" variant="contained" size="large">Về trang chủ</Button>
    </Stack>
  );
}
