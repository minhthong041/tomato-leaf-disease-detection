import BookmarkIcon from '@mui/icons-material/Bookmark';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import HistoryIcon from '@mui/icons-material/History';
import ImageNotSupportedOutlinedIcon from '@mui/icons-material/ImageNotSupportedOutlined';
import {
  Alert, Avatar, Box, Button, Card, Chip, CircularProgress, List, ListItemButton, Pagination, Stack,
  ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { errorMessage } from '../api/client';
import { listDiagnoses } from '../api/diagnoses';
import PageHeader from '../components/PageHeader';
import { SEVERITY_LEVELS, STATUS_LABELS, formatPercent } from '../constants/diagnosis';

const PAGE_SIZE = 20; // trùng PAGE_SIZE của DRF
const FILTER_PARAM = 'filter'; // ?filter=saved giữ bộ lọc khi quay lại từ trang kết quả
const FILTER_ALL = 'all';
const FILTER_SAVED = 'saved';

export default function HistoryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filter = searchParams.get(FILTER_PARAM) === FILTER_SAVED ? FILTER_SAVED : FILTER_ALL;
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    listDiagnoses(page, { bookmarkedOnly: filter === FILTER_SAVED })
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(errorMessage(err)));
    return () => {
      cancelled = true;
    };
  }, [page, filter]);

  // Đổi bộ lọc hoặc trang: xóa dữ liệu cũ để hiện vòng tải thay vì danh sách cũ
  function resetList() {
    setData(null);
    setError('');
  }

  function handleFilterChange(_, value) {
    if (!value || value === filter) return; // bấm lại nút đang chọn: giữ nguyên
    resetList();
    setPage(1);
    setSearchParams(value === FILTER_SAVED ? { [FILTER_PARAM]: FILTER_SAVED } : {});
  }

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
          <Card>
            <List disablePadding>
              {data.results.map((item, index) => {
                const level = SEVERITY_LEVELS[item.severity_level];
                const done = item.status === 'done';
                return (
                  <ListItemButton key={item.id} component={Link} to={`/results/${item.id}`}
                    divider={index < data.results.length - 1}
                    sx={{ gap: 2, py: 1.5, px: { xs: 2, sm: 2.5 }, alignItems: 'center' }}>
                    <Avatar variant="rounded" src={item.original_image} alt=""
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
          {data.count > PAGE_SIZE && (
            <Pagination count={Math.ceil(data.count / PAGE_SIZE)} page={page} color="primary"
              onChange={(_, value) => { if (value !== page) { resetList(); setPage(value); } }} sx={{ alignSelf: 'center' }} />
          )}
        </>
      )}
    </Stack>
  );
}
