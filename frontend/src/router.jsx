import { createBrowserRouter } from 'react-router';

import RequireAuth from './auth/RequireAuth';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';

// Các trang sau đăng nhập được tách thành file JS riêng, chỉ tải khi mở trang
const page = (load) => () => load().then((module) => ({ Component: module.default }));

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      {
        element: <RequireAuth />,
        children: [
          { path: '/', lazy: page(() => import('./pages/UploadPage')) },
          { path: '/results/:id', lazy: page(() => import('./pages/ResultPage')) },
          { path: '/history', lazy: page(() => import('./pages/HistoryPage')) },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export default router;
