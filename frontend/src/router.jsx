import { createBrowserRouter } from 'react-router';

import RequireAuth from './auth/RequireAuth';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';

// Các trang (trừ đăng nhập) được tách thành file JS riêng, chỉ tải khi mở trang
const page = (load) => () => load().then((module) => ({ Component: module.default }));

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      // Trang công khai, không cần đăng nhập
      { path: '/register', lazy: page(() => import('./pages/RegisterPage')) },
      { path: '/terms', lazy: page(() => import('./pages/TermsPage')) },
      {
        element: <RequireAuth />,
        children: [
          { path: '/', lazy: page(() => import('./pages/UploadPage')) },
          { path: '/results/:id', lazy: page(() => import('./pages/ResultPage')) },
          { path: '/history', lazy: page(() => import('./pages/HistoryPage')) },
          { path: '/error-report', lazy: page(() => import('./pages/ErrorReportPage')) },
          { path: '/account', lazy: page(() => import('./pages/AccountPage')) },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export default router;
