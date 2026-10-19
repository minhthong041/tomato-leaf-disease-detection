import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import HistoryIcon from '@mui/icons-material/History';
import LogoutIcon from '@mui/icons-material/Logout';
import SpaIcon from '@mui/icons-material/Spa';
import { AppBar, Box, Button, Container, Toolbar, Typography } from '@mui/material';
import { Link, Outlet, useNavigate } from 'react-router';

import { useAuth } from '../auth/context';

export default function Layout() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppBar position="static" elevation={0}>
        <Toolbar sx={{ gap: 1, flexWrap: 'wrap' }}>
          <SpaIcon />
          <Typography variant="h6" component={Link} to="/"
            sx={{ flexGrow: 1, color: 'inherit', textDecoration: 'none' }}>
            Chẩn Đoán Bệnh Lá Cà Chua
          </Typography>
          {isAuthenticated && (
            <>
              <Button color="inherit" component={Link} to="/" startIcon={<CloudUploadIcon />}>
                Tải ảnh
              </Button>
              <Button color="inherit" component={Link} to="/history" startIcon={<HistoryIcon />}>
                Lịch sử
              </Button>
              <Button color="inherit" onClick={handleLogout} startIcon={<LogoutIcon />}>
                Đăng xuất
              </Button>
            </>
          )}
        </Toolbar>
      </AppBar>
      <Container maxWidth="md" sx={{ py: 4, flexGrow: 1 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
