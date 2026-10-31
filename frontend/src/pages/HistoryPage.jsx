import BookmarkIcon from '@mui/icons-material/Bookmark';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import HistoryIcon from '@mui/icons-material/History';
import ImageNotSupportedOutlinedIcon from '@mui/icons-material/ImageNotSupportedOutlined';
import {
  Alert, Avatar, Box, Button, Card, Chip, CircularProgress, List, ListItemButton, Pagination, Stack,
  ToggleButton, ToggleButtonGroup, Typography, useMediaQuery,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { ApiError, errorMessage } from '../api/client';
import { listDiagnoses } from '../api/diagnoses';
import PageHeader from '../components/PageHeader';
import { SEVERITY_LEVELS, STATUS_LABELS, formatPercent } from '../constants/diagnosis';

const PAGE_SIZE = 20; // trùng PAGE_SIZE của DRF
// Bộ lọc và số trang nằm trên URL (?filter=saved&page=2) để quay lại từ trang kết quả vẫn đúng chỗ
const FILTER_PARAM = 'filter';
const PAGE_PARAM = 'page';
const FILTER_ALL = 'all';
const FILTER_SAVED = 'saved';

function historyParams(filter, page) {
  const params = {};
  if (filter === FILTER_SAVED) params[FILTER_PARAM] = FILTER_SAVED;
  if (page > 1) params[PAGE_PARAM] = String(page);
  return params;
}

export default function HistoryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filter = searchParams.get(FILTER_PARAM) === FILTER_SAVED ? FILTER_SAVED : FILTER_ALL;
  const page = Math.max(1, Number.parseInt(searchParams.get(PAGE_PARAM), 10) || 1);
  const isPhone = useMediaQuery((theme) => theme.breakpoints.down('sm'));
  // Kết quả gắn với bộ lọc + trang đã tải; đổi bộ lọc/trang (kể cả nút Back) thì hiện vòng tải thay vì danh sách cũ
  const queryKey = `${filter}:${page}`;
  const [loaded, setLoaded] = useState({ key: null, data: null, error: '' });
  const data = loaded.key === queryKey ? loaded.data : null;
  const error = loaded.key === queryKey ? loaded.error : '';

  useEffect(() => {
    let cancelled = false;
    listDiagnoses(page, { bookmarkedOnly: filter === FILTER_SAVED })
      .then((result) => !cancelled && setLoaded({ key: queryKey, data: result, error: '' }))
      .catch((err) => {
        if (cancelled) return;
        // Trang không còn tồn tại (đường dẫn cũ, hoặc bỏ lưu làm bớt số trang): về trang 1
        if (err instanceof ApiError && err.status === 404 && page > 1) {
          setSearchParams(historyParams(filter, 1), { replace: true });
          return;
        }
        setLoaded({ key: queryKey, data: null, error: errorMessage(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [filter, page, queryKey, setSearchParams]);

  function handleFilterChange(_, value) {
    if (!value || value === filter) return; // bấm lại nút đang chọn: giữ nguyên
    setSearchParams(historyParams(value, 1));
  }

  function handlePageChange(_, value) {
    if (value === page) return;
    setSearchParams(historyParams(filter, value));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  const pageCount = data ? Math.ceil(data.count / PAGE_SIZE) : 0;
  const firstShown = (page - 1) * PAGE_SIZE + 1;

  const emptyText = filter === FILTER_SAVED
    ? 'Chưa lưu kết quả nào. Bấm "Lưu kết quả" trên trang kết quả để lưu lại.'
    : 'Chưa có lần chẩn đoán nào.';

  return (
    <Stack spacing={3}>
      <PageHeader
        overline="Kết quả đã chẩn đoán"
        title="Lịch sử chẩn đoán"
        actions={(
          <ToggleButtonGroup size="small" exclusive value={filter} onChange={handleFilterChange}
            aria-label="Lọc lịch sử" sx={{ bgcolor: 'background.paper' }}>
            <ToggleButton value={FILTER_ALL} sx={{ px: 2 }}>Tất cả</ToggleButton>
            <ToggleButton value={FILTER_SAVED} sx={{ px: 2 }}>
              <BookmarkIcon fontSize="small" sx={{ mr: 0.5 }} />
              Đã lưu
            </ToggleButton>
          </ToggleButtonGroup>
        )}
      />
      {error && <Alert severity="error">{error}</Alert>}
      {!data && !error && <Box sx={{ display: 'grid', placeItems: 'center', py: 8 }}><CircularProgress /></Box>}
      {data && data.results.length === 0 && (
        <Card>
          <Stack spacing={1.5} sx={{ py: 6, px: 3, alignItems: 'center', textAlign: 'center' }}>
            <Avatar sx={{ width: 56, height: 56, bgcolor: 'primary.light', color: 'primary.main' }}>
              <HistoryIcon />
            </Avatar>
            <Typography color="text.secondary">{emptyText}</Typography>
            {filter === FILTER_ALL && (
              <Button component={Link} to="/" variant="contained">Chẩn đoán ảnh đầu tiên</Button>
            )}
          </Stack>
        </Card>
      )}
      {data && data.results.length > 0 && (
        <>
          <Typography variant="body2" color="text.secondary" aria-live="polite" sx={{ mb: -1.5 }}>
            {pageCount > 1
              ? `Hiển thị ${firstShown}–${firstShown + data.results.length - 1} trong ${data.count} kết quả · Trang ${page}/${pageCount}`
              : `${data.count} kết quả`}
          </Typography>
          <Card>
            <List disablePadding>
              {data.results.map((item, index) => {
                const level = SEVERITY_LEVELS[item.severity_level];
                const done = item.status === 'done';
                return (
                  <ListItemButton key={item.id} component={Link} to={`/results/${item.id}`}
                    divider={index < data.results.length - 1}
                    sx={{ gap: 2, py: 1.5, px: { xs: 2, sm: 2.5 }, alignItems: 'center' }}>
                    {/* Ảnh kết quả 512px nhẹ hơn ảnh gốc (tới 10 MB); lần chẩn đoán lỗi không có thì dùng ảnh gốc */}
                    <Avatar variant="rounded" src={item.processed_image || item.original_image} alt=""
                      slotProps={{ img: { loading: 'lazy' } }}
                      sx={{ width: 56, height: 56, borderRadius: '8px', bgcolor: 'grey.100', color: 'text.disabled' }}>
                      <ImageNotSupportedOutlinedIcon />
                    </Avatar>
                    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                      <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
                        <Typography sx={{ fontWeight: 600 }} noWrap>
                          {done ? (item.disease?.name ?? '—') : STATUS_LABELS[item.status]}
                        </Typography>
                        {item.is_bookmarked && (
                          <BookmarkIcon color="primary" fontSize="small" titleAccess="Đã lưu" />
                        )}
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(item.created_at).toLocaleString('vi-VN')}
                      </Typography>
                      {level && (
                        <Chip size="small" label={`${level.label} · ${formatPercent(item.infected_ratio)}`}
                          sx={{ display: { xs: 'inline-flex', sm: 'none' }, mt: 0.75, bgcolor: level.color, color: 'common.white' }} />
                      )}
                    </Box>
                    {level && (
                      <Chip label={`${level.label} · ${formatPercent(item.infected_ratio)}`}
                        sx={{ display: { xs: 'none', sm: 'inline-flex' }, bgcolor: level.color, color: 'common.white' }} />
                    )}
                    <ChevronRightIcon sx={{ color: 'text.disabled', display: { xs: 'none', sm: 'block' } }} />
                  </ListItemButton>
                );
              })}
            </List>
          </Card>
          {pageCount > 1 && (
            <Pagination count={pageCount} page={page} onChange={handlePageChange}
              color="primary" shape="rounded" showFirstButton showLastButton
              siblingCount={isPhone ? 0 : 1} size={isPhone ? 'medium' : 'large'}
              getItemAriaLabel={(type, item, selected) => {
                if (type === 'page') return selected ? `Trang ${item}, đang xem` : `Đến trang ${item}`;
                return { first: 'Trang đầu', last: 'Trang cuối', next: 'Trang sau', previous: 'Trang trước' }[type];
              }}
              sx={{ alignSelf: 'center', '& .MuiPaginationItem-root': { fontWeight: 600 } }} />
          )}
        </>
      )}
    </Stack>
  );
}
