import { Button, Stack, Typography } from '@mui/material';
import { Link } from 'react-router';

export default function NotFoundPage() {
  return (
    <Stack spacing={2} sx={{ py: 8, alignItems: 'center' }}>
      <Typography variant="h4" component="h1">Không tìm thấy trang</Typography>
      <Button component={Link} to="/" variant="contained">Về trang chủ</Button>
    </Stack>
  );
}
