import BugReportOutlinedIcon from '@mui/icons-material/BugReportOutlined';
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import HistoryIcon from '@mui/icons-material/History';
import LogoutIcon from '@mui/icons-material/Logout';
import ManageAccountsOutlinedIcon from '@mui/icons-material/ManageAccountsOutlined';
import {
  AppBar, BottomNavigation, BottomNavigationAction, Box, Button, Container, IconButton, Link, Paper, Stack,
  Toolbar, Tooltip, Typography,
} from '@mui/material';
import { Outlet, Link as RouterLink, useLocation, useNavigate } from 'react-router';

import { useAuth } from '../auth/context';
import BrandMark from './BrandMark';

// Mục menu sau khi đăng nhập. Desktop: nút trên thanh đầu; điện thoại: thanh điều hướng dưới đáy.
const NAV_ITEMS = [
  { to: '/', label: 'Tải ảnh', icon: <CloudUploadOutlinedIcon /> },
  { to: '/history', label: 'Lịch sử', icon: <HistoryIcon /> },
  { to: '/error-report', label: 'Báo lỗi', icon: <BugReportOutlinedIcon /> },
  { to: '/account', label: 'Tài khoản', icon: <ManageAccountsOutlinedIcon /> },
];
const BOTTOM_NAV_HEIGHT = 64;

export default function Layout() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  // Trang kết quả không thuộc mục nào nên không tô mục nào
  const activeItem = NAV_ITEMS.find((item) => item.to === pathname)?.to ?? false;

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppBar position="sticky" color="inherit" elevation={0}
        sx={{ bgcolor: 'rgba(255, 255, 255, 0.92)', backdropFilter: 'blur(8px)', borderBottom: 1, borderColor: 'divider' }}>
        <Container maxWidth="lg" disableGutters>
          <Toolbar sx={{ gap: 1, minHeight: { xs: 60, md: 68 } }}>
            <Stack direction="row" spacing={1.25} component={RouterLink} to="/"
              sx={{ alignItems: 'center', flexGrow: 1, minWidth: 0, color: 'inherit', textDecoration: 'none' }}>
              <BrandMark />
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ fontWeight: 700, lineHeight: 1.2, fontSize: { xs: '1rem', sm: '1.1rem' } }} noWrap>
                  Chẩn Đoán Bệnh Lá Cà Chua
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap
                  sx={{ display: { xs: 'none', sm: 'block' }, lineHeight: 1.2 }}>
                  Tách lá · tìm vết bệnh · chấm cấp độ 0–4
                </Typography>
              </Box>
            </Stack>

            {isAuthenticated ? (
              <>
                <Stack direction="row" spacing={0.5} component="nav" aria-label="Menu chính"
                  sx={{ display: { xs: 'none', md: 'flex' } }}>
                  {NAV_ITEMS.map((item) => {
                    const active = item.to === activeItem;
                    return (
                      <Button key={item.to} component={RouterLink} to={item.to} startIcon={item.icon}
                        aria-current={active ? 'page' : undefined}
                        sx={{
                          color: active ? 'primary.main' : 'text.secondary',
                          bgcolor: active ? 'primary.light' : 'transparent',
                          px: 1.5,
                        }}>
                        {item.label}
                      </Button>
                    );
                  })}
                  <Button onClick={handleLogout} startIcon={<LogoutIcon />} sx={{ color: 'text.secondary', px: 1.5 }}>
                    Đăng xuất
                  </Button>
                </Stack>
                <Tooltip title="Đăng xuất">
                  <IconButton onClick={handleLogout} aria-label="Đăng xuất" edge="end"
                    sx={{ display: { xs: 'inline-flex', md: 'none' } }}>
                    <LogoutIcon />
                  </IconButton>
                </Tooltip>
              </>
            ) : (
              <Button component={RouterLink} to={pathname === '/login' ? '/register' : '/login'} variant="outlined"
                sx={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
                {pathname === '/login' ? 'Đăng ký' : 'Đăng nhập'}
              </Button>
            )}
          </Toolbar>
        </Container>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 }, flexGrow: 1 }}>
        <Outlet />
      </Container>

      <Box component="footer" sx={{
        py: 3, px: 2, textAlign: 'center', borderTop: 1, borderColor: 'divider',
        mb: isAuthenticated ? { xs: `${BOTTOM_NAV_HEIGHT}px`, md: 0 } : 0,
      }}>
        <Typography variant="body2" color="text.secondary">
          Đồ án môn Xử lý ảnh · Kết quả chỉ để tham khảo, không thay thế ý kiến chuyên gia ·{' '}
          <Link component={RouterLink} to="/terms" color="inherit">Điều khoản sử dụng</Link>
        </Typography>
      </Box>

      {isAuthenticated && (
        <Paper component="nav" aria-label="Menu chính" square elevation={0} sx={{
          display: { xs: 'block', md: 'none' }, position: 'fixed', left: 0, right: 0, bottom: 0,
          zIndex: (theme) => theme.zIndex.appBar, borderTop: 1, borderColor: 'divider',
          pb: 'env(safe-area-inset-bottom)',
        }}>
          <BottomNavigation showLabels value={activeItem} sx={{ height: BOTTOM_NAV_HEIGHT }}>
            {NAV_ITEMS.map((item) => (
              <BottomNavigationAction key={item.to} value={item.to} label={item.label} icon={item.icon}
                component={RouterLink} to={item.to} aria-current={item.to === activeItem ? 'page' : undefined}
                sx={{ minWidth: 0, '& .MuiBottomNavigationAction-label': { fontWeight: 600, mt: 0.25 } }} />
            ))}
          </BottomNavigation>
        </Paper>
      )}
    </Box>
  );
}
